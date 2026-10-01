import cv2
import mediapipe as mp
import math
import time


class PoseDetector:
    def __init__(
        self,
        model_path="models/pose_landmarker_lite.task"
    ):
        # =====================================
        # MediaPipe Tasks 初始化
        # =====================================

        BaseOptions = mp.tasks.BaseOptions

        PoseLandmarker = (
            mp.tasks.vision.PoseLandmarker
        )

        PoseLandmarkerOptions = (
            mp.tasks.vision.PoseLandmarkerOptions
        )

        RunningMode = (
            mp.tasks.vision.RunningMode
        )

        # =====================================
        # VIDEO 模式
        #
        # 与之前 IMAGE 最大的区别：
        # MediaPipe 知道前后帧属于连续视频
        # =====================================

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(
                model_asset_path=model_path
            ),

            running_mode=RunningMode.VIDEO,

            num_poses=1,

            min_pose_detection_confidence=0.5,

            min_pose_presence_confidence=0.5,

            min_tracking_confidence=0.5,
        )

        self.landmarker = (
            PoseLandmarker.create_from_options(
                options
            )
        )

        # =====================================
        # VIDEO 时间戳
        # =====================================

        self.start_time = time.perf_counter()

        self.last_timestamp_ms = -1

        # =====================================
        # 保存上一帧平滑后的关键点
        # =====================================

        self.smoothed_landmarks = {}

        self.current_landmarks = {}

        # =====================================
        # 可见度阈值
        # =====================================

        self.min_visibility = 0.45

        # =====================================
        # 自适应平滑参数
        #
        # 静止时：
        # alpha 小 -> 更稳定
        #
        # 快速运动：
        # alpha 大 -> 跟得更快
        # =====================================

        self.static_alpha = 0.12

        self.moving_alpha = 0.55

        # =====================================
        # 判断运动速度的距离
        # =====================================

        self.motion_low = 0.005

        self.motion_high = 0.040

        # =====================================
        # 异常跳点阈值
        # =====================================

        self.max_jump = 0.12

        # =====================================
        # 人体丢失计数
        # =====================================

        self.lost_frames = 0

        self.max_lost_frames = 15

    # =========================================
    # 两点距离
    # =========================================

    def distance(
        self,
        point_a,
        point_b
    ):
        dx = (
            point_a[0]
            -
            point_b[0]
        )

        dy = (
            point_a[1]
            -
            point_b[1]
        )

        return math.sqrt(
            dx * dx
            +
            dy * dy
        )

    # =========================================
    # 根据移动速度决定平滑强度
    # =========================================

    def get_adaptive_alpha(
        self,
        movement
    ):
        # -------------------------------------
        # 几乎不动
        # 强平滑
        # -------------------------------------

        if movement <= self.motion_low:

            return self.static_alpha

        # -------------------------------------
        # 快速运动
        # 更快跟随
        # -------------------------------------

        if movement >= self.motion_high:

            return self.moving_alpha

        # -------------------------------------
        # 中间速度
        # 自动插值
        # -------------------------------------

        ratio = (
            movement
            -
            self.motion_low
        ) / (
            self.motion_high
            -
            self.motion_low
        )

        alpha = (
            self.static_alpha
            +
            ratio
            *
            (
                self.moving_alpha
                -
                self.static_alpha
            )
        )

        return alpha

    # =========================================
    # 单个关键点平滑
    # =========================================

    def smooth_point(
        self,
        index,
        x,
        y,
        visibility
    ):
        new_point = (
            x,
            y
        )

        # -------------------------------------
        # 第一次出现
        # -------------------------------------

        if (
            index
            not in
            self.smoothed_landmarks
        ):

            self.smoothed_landmarks[
                index
            ] = new_point

            return new_point

        previous_point = (
            self.smoothed_landmarks[
                index
            ]
        )

        # -------------------------------------
        # 可见度低
        #
        # 暂时继续沿用上一帧
        # -------------------------------------

        if (
            visibility
            <
            self.min_visibility
        ):

            return previous_point

        # -------------------------------------
        # 当前帧相比上一帧移动距离
        # -------------------------------------

        movement = self.distance(
            previous_point,
            new_point
        )

        # -------------------------------------
        # 自适应 alpha
        # -------------------------------------

        alpha = self.get_adaptive_alpha(
            movement
        )

        # -------------------------------------
        # 极端跳点
        #
        # 不完全相信这一帧
        # -------------------------------------

        if movement > self.max_jump:

            alpha = 0.08

        # -------------------------------------
        # EMA 时序平滑
        # -------------------------------------

        smooth_x = (
            previous_point[0]
            +
            alpha
            *
            (
                x
                -
                previous_point[0]
            )
        )

        smooth_y = (
            previous_point[1]
            +
            alpha
            *
            (
                y
                -
                previous_point[1]
            )
        )

        smooth_point = (
            smooth_x,
            smooth_y
        )

        self.smoothed_landmarks[
            index
        ] = smooth_point

        return smooth_point

    # =========================================
    # 生成 VIDEO 模式要求的时间戳
    # =========================================

    def get_timestamp_ms(
        self
    ):
        timestamp_ms = int(
            (
                time.perf_counter()
                -
                self.start_time
            )
            *
            1000
        )

        # MediaPipe VIDEO 要求时间戳严格递增
        if (
            timestamp_ms
            <=
            self.last_timestamp_ms
        ):

            timestamp_ms = (
                self.last_timestamp_ms
                +
                1
            )

        self.last_timestamp_ms = (
            timestamp_ms
        )

        return timestamp_ms

    # =========================================
    # 人体检测
    # =========================================

    def detect(
        self,
        frame
    ):
        # OpenCV BGR -> RGB
        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        timestamp_ms = (
            self.get_timestamp_ms()
        )

        # =====================================
        # VIDEO 模式核心
        # =====================================

        result = (
            self.landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )
        )

        self.current_landmarks = {}

        # =====================================
        # 检测到人体
        # =====================================

        if result.pose_landmarks:

            self.lost_frames = 0

            landmarks = (
                result.pose_landmarks[0]
            )

            height, width, _ = (
                frame.shape
            )

            for (
                index,
                landmark
            ) in enumerate(
                landmarks
            ):

                # ---------------------------------
                # 前后帧关键点平滑
                # ---------------------------------

                (
                    smooth_x,
                    smooth_y
                ) = self.smooth_point(
                    index,
                    landmark.x,
                    landmark.y,
                    landmark.visibility
                )

                # ---------------------------------
                # 保存平滑后的坐标
                # ---------------------------------

                self.current_landmarks[
                    index
                ] = {
                    "point": (
                        smooth_x,
                        smooth_y
                    ),

                    "visibility":
                        landmark.visibility
                }

                # ---------------------------------
                # 绘制平滑后的绿色点
                # ---------------------------------

                if (
                    landmark.visibility
                    >=
                    self.min_visibility
                ):

                    pixel_x = int(
                        smooth_x
                        *
                        width
                    )

                    pixel_y = int(
                        smooth_y
                        *
                        height
                    )

                    cv2.circle(
                        frame,
                        (
                            pixel_x,
                            pixel_y
                        ),
                        5,
                        (
                            0,
                            255,
                            0
                        ),
                        -1
                    )

        # =====================================
        # 暂时没有识别到人体
        # =====================================

        else:

            self.lost_frames += 1

            # 不因为偶尔一帧丢失
            # 就把历史轨迹全部删除
            if (
                self.lost_frames
                >
                self.max_lost_frames
            ):

                self.smoothed_landmarks.clear()

                self.current_landmarks.clear()

        return (
            frame,
            result
        )

    # =========================================
    # 给其他模块读取关键点
    # =========================================

    def get_landmark(
        self,
        result,
        index
    ):
        if (
            index
            not in
            self.current_landmarks
        ):

            return None

        return (
            self.current_landmarks[
                index
            ]
        )

    # =========================================
    # 主动重置平滑数据
    # =========================================

    def reset_smoothing(
        self
    ):
        self.smoothed_landmarks.clear()

        self.current_landmarks.clear()

        self.lost_frames = 0