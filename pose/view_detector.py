import math


class ViewDetector:
    def __init__(self):
        # 当前稳定视角
        self.current_view = "CALIBRATING"

        # 候选视角
        self.candidate_view = None
        self.candidate_frames = 0

        # 连续多少帧确认视角
        self.required_frames = 12

        # =====================================
        # 根据你实测数据重新校准
        #
        # 正面约：0.56
        # 完全侧面约：0.10
        #
        # 所以：
        # <= 0.22 认为 SIDE
        # >= 0.42 认为 FRONT
        # 0.22 ~ 0.42 认为 TRANSITION
        # =====================================

        self.side_threshold = 0.22

        self.front_threshold = 0.42

    def distance(
        self,
        point_a,
        point_b,
        aspect_ratio
    ):
        """
        MediaPipe 坐标为归一化坐标。

        对 X 方向做宽高比修正，
        避免 16:9 等画面比例造成失真。
        """

        dx = (
            point_a[0]
            -
            point_b[0]
        ) * aspect_ratio

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

    def calculate_view_ratio(
        self,
        left_shoulder,
        right_shoulder,
        left_hip,
        right_hip,
        frame_width,
        frame_height
    ):
        if frame_height == 0:
            return 0.0

        aspect_ratio = (
            frame_width
            /
            frame_height
        )

        # 左右肩宽
        shoulder_width = self.distance(
            left_shoulder,
            right_shoulder,
            aspect_ratio
        )

        # 左右髋宽
        hip_width = self.distance(
            left_hip,
            right_hip,
            aspect_ratio
        )

        # 左侧躯干长度
        left_torso = self.distance(
            left_shoulder,
            left_hip,
            aspect_ratio
        )

        # 右侧躯干长度
        right_torso = self.distance(
            right_shoulder,
            right_hip,
            aspect_ratio
        )

        average_body_width = (
            shoulder_width
            +
            hip_width
        ) / 2

        average_torso_length = (
            left_torso
            +
            right_torso
        ) / 2

        if average_torso_length < 0.001:
            return 0.0

        ratio = (
            average_body_width
            /
            average_torso_length
        )

        return ratio

    def classify_raw_view(
        self,
        ratio
    ):
        # =====================================
        # 明显侧面
        # =====================================

        if ratio <= self.side_threshold:
            return "SIDE"

        # =====================================
        # 明显正面
        # =====================================

        if ratio >= self.front_threshold:
            return "FRONT"

        # =====================================
        # 中间视角
        # =====================================

        return "TRANSITION"

    def update(
        self,
        left_shoulder,
        right_shoulder,
        left_hip,
        right_hip,
        frame_width,
        frame_height,
        freeze=False
    ):
        # =====================================
        # 计算当前视角比例
        # =====================================

        ratio = self.calculate_view_ratio(
            left_shoulder,
            right_shoulder,
            left_hip,
            right_hip,
            frame_width,
            frame_height
        )

        # =====================================
        # 当前原始视角
        # =====================================

        raw_view = self.classify_raw_view(
            ratio
        )

        # =====================================
        # 深蹲过程中锁定当前稳定视角
        #
        # 防止动作本身造成 FRONT / SIDE
        # 来回变化
        # =====================================

        if freeze:

            return (
                self.current_view,
                ratio,
                raw_view
            )

        # =====================================
        # TRANSITION 不立即切换
        # =====================================

        if raw_view == "TRANSITION":

            self.candidate_view = None

            self.candidate_frames = 0

            return (
                self.current_view,
                ratio,
                raw_view
            )

        # =====================================
        # 连续观察同一种候选视角
        # =====================================

        if raw_view == self.candidate_view:

            self.candidate_frames += 1

        else:

            self.candidate_view = raw_view

            self.candidate_frames = 1

        # =====================================
        # 连续达到要求帧数
        # 才正式切换
        # =====================================

        if (
            self.candidate_frames
            >=
            self.required_frames
        ):

            self.current_view = raw_view

            self.candidate_view = None

            self.candidate_frames = 0

        return (
            self.current_view,
            ratio,
            raw_view
        )