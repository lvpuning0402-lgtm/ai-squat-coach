from collections import deque


class FrontFeedback:
    def __init__(self):
        # =====================================
        # 平滑窗口
        # =====================================

        self.left_valgus_buffer = deque(
            maxlen=10
        )

        self.right_valgus_buffer = deque(
            maxlen=10
        )

        self.symmetry_buffer = deque(
            maxlen=10
        )

        # =====================================
        # 膝盖内偏阈值
        #
        # 这部分暂时保持原值，
        # 等你单独测试膝内扣数据后再校准
        # =====================================

        self.valgus_bad_threshold = 0.18

        self.valgus_good_threshold = 0.12

        # =====================================
        # 左右不对称阈值
        #
        # 根据你实际测试重新校准：
        #
        # 正常深蹲约：
        # 0.25
        #
        # 故意明显偏侧约：
        # 1.09
        #
        # 所以：
        #
        # < 0.35
        # 认为基本对称
        #
        # 0.35 ~ 0.60
        # 缓冲区
        #
        # > 0.60
        # 认为明显不对称
        # =====================================

        self.symmetry_good_threshold = 0.35

        self.symmetry_bad_threshold = 0.60

        # =====================================
        # 连续帧确认
        # =====================================

        self.required_frames = 7

        # =====================================
        # 膝盖状态帧计数
        # =====================================

        self.left_bad_frames = 0
        self.right_bad_frames = 0

        self.left_good_frames = 0
        self.right_good_frames = 0

        # =====================================
        # 对称状态帧计数
        # =====================================

        self.symmetry_bad_frames = 0

        self.symmetry_good_frames = 0

        # =====================================
        # 当前稳定状态
        # =====================================

        self.left_knee_state = "OK"

        self.right_knee_state = "OK"

        self.symmetry_state = "OK"

    def average(
        self,
        buffer
    ):
        if not buffer:
            return 0.0

        return (
            sum(buffer)
            /
            len(buffer)
        )

    def calculate_metrics(
        self,
        left_hip,
        right_hip,
        left_knee,
        right_knee,
        left_ankle,
        right_ankle
    ):
        # =====================================
        # 身体中线
        # =====================================

        mid_x = (
            left_hip[0]
            +
            right_hip[0]
        ) / 2

        # =====================================
        # 髋宽
        #
        # 用作归一化，
        # 减少人与摄像头距离的影响
        # =====================================

        hip_width = abs(
            right_hip[0]
            -
            left_hip[0]
        )

        if hip_width < 0.01:
            hip_width = 0.01

        # =====================================
        # 左膝向内程度
        # =====================================

        left_knee_mid_distance = abs(
            left_knee[0]
            -
            mid_x
        )

        left_ankle_mid_distance = abs(
            left_ankle[0]
            -
            mid_x
        )

        left_valgus = (
            left_ankle_mid_distance
            -
            left_knee_mid_distance
        ) / hip_width

        # =====================================
        # 右膝向内程度
        # =====================================

        right_knee_mid_distance = abs(
            right_knee[0]
            -
            mid_x
        )

        right_ankle_mid_distance = abs(
            right_ankle[0]
            -
            mid_x
        )

        right_valgus = (
            right_ankle_mid_distance
            -
            right_knee_mid_distance
        ) / hip_width

        # =====================================
        # 左右膝高度差
        #
        # 越大表示左右下降程度越不一致
        # =====================================

        knee_height_difference = abs(
            left_knee[1]
            -
            right_knee[1]
        )

        symmetry_ratio = (
            knee_height_difference
            /
            hip_width
        )

        return (
            left_valgus,
            right_valgus,
            symmetry_ratio
        )

    def update_knee_state(
        self,
        value,
        side
    ):
        # =====================================
        # 明显向内
        # =====================================

        if (
            value
            >
            self.valgus_bad_threshold
        ):

            if side == "LEFT":

                self.left_bad_frames += 1

                self.left_good_frames = 0

                if (
                    self.left_bad_frames
                    >=
                    self.required_frames
                ):

                    self.left_knee_state = (
                        "KNEE IN"
                    )

            else:

                self.right_bad_frames += 1

                self.right_good_frames = 0

                if (
                    self.right_bad_frames
                    >=
                    self.required_frames
                ):

                    self.right_knee_state = (
                        "KNEE IN"
                    )

        # =====================================
        # 回到正常范围
        # =====================================

        elif (
            value
            <
            self.valgus_good_threshold
        ):

            if side == "LEFT":

                self.left_good_frames += 1

                self.left_bad_frames = 0

                if (
                    self.left_good_frames
                    >=
                    self.required_frames
                ):

                    self.left_knee_state = "OK"

            else:

                self.right_good_frames += 1

                self.right_bad_frames = 0

                if (
                    self.right_good_frames
                    >=
                    self.required_frames
                ):

                    self.right_knee_state = "OK"

        # =====================================
        # 缓冲区
        # =====================================

        else:

            if side == "LEFT":

                self.left_bad_frames = 0

                self.left_good_frames = 0

            else:

                self.right_bad_frames = 0

                self.right_good_frames = 0

        if side == "LEFT":

            return self.left_knee_state

        return self.right_knee_state

    def update_symmetry_state(
        self,
        value
    ):
        # =====================================
        # 明显左右不对称
        # =====================================

        if (
            value
            >
            self.symmetry_bad_threshold
        ):

            self.symmetry_bad_frames += 1

            self.symmetry_good_frames = 0

            if (
                self.symmetry_bad_frames
                >=
                self.required_frames
            ):

                self.symmetry_state = (
                    "ASYMMETRIC"
                )

        # =====================================
        # 明显回到正常范围
        # =====================================

        elif (
            value
            <
            self.symmetry_good_threshold
        ):

            self.symmetry_good_frames += 1

            self.symmetry_bad_frames = 0

            if (
                self.symmetry_good_frames
                >=
                self.required_frames
            ):

                self.symmetry_state = "OK"

        # =====================================
        # 0.35 ~ 0.60
        #
        # 缓冲区
        # 保持之前的稳定判断
        # =====================================

        else:

            self.symmetry_bad_frames = 0

            self.symmetry_good_frames = 0

        return self.symmetry_state

    def update(
        self,
        left_hip,
        right_hip,
        left_knee,
        right_knee,
        left_ankle,
        right_ankle,
        stage
    ):
        (
            left_valgus,
            right_valgus,
            symmetry
        ) = self.calculate_metrics(
            left_hip,
            right_hip,
            left_knee,
            right_knee,
            left_ankle,
            right_ankle
        )

        # =====================================
        # 数据平滑
        # =====================================

        self.left_valgus_buffer.append(
            left_valgus
        )

        self.right_valgus_buffer.append(
            right_valgus
        )

        self.symmetry_buffer.append(
            symmetry
        )

        smooth_left = self.average(
            self.left_valgus_buffer
        )

        smooth_right = self.average(
            self.right_valgus_buffer
        )

        smooth_symmetry = self.average(
            self.symmetry_buffer
        )

        # =====================================
        # 站立阶段
        #
        # 只显示 READY
        # 不判断动作错误
        # =====================================

        if stage != "down":

            return {
                "left_state":
                    "READY",

                "right_state":
                    "READY",

                "symmetry_state":
                    "READY",

                "left_value":
                    smooth_left,

                "right_value":
                    smooth_right,

                "symmetry_value":
                    smooth_symmetry
            }

        # =====================================
        # 下蹲阶段
        # =====================================

        left_state = (
            self.update_knee_state(
                smooth_left,
                "LEFT"
            )
        )

        right_state = (
            self.update_knee_state(
                smooth_right,
                "RIGHT"
            )
        )

        symmetry_state = (
            self.update_symmetry_state(
                smooth_symmetry
            )
        )

        return {
            "left_state":
                left_state,

            "right_state":
                right_state,

            "symmetry_state":
                symmetry_state,

            "left_value":
                smooth_left,

            "right_value":
                smooth_right,

            "symmetry_value":
                smooth_symmetry
        }

    def reset(
        self
    ):
        self.left_valgus_buffer.clear()

        self.right_valgus_buffer.clear()

        self.symmetry_buffer.clear()

        self.left_bad_frames = 0

        self.right_bad_frames = 0

        self.left_good_frames = 0

        self.right_good_frames = 0

        self.symmetry_bad_frames = 0

        self.symmetry_good_frames = 0

        self.left_knee_state = "OK"

        self.right_knee_state = "OK"

        self.symmetry_state = "OK"