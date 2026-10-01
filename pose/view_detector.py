from collections import deque
from statistics import median
import math


class ViewDetector:
    """
    FRONT / SIDE / TRANSITION 视角状态机。

    目标：
    - 转身过程中明确进入 TRANSITION
    - 不在身体还没完全正对镜头时过早切到 FRONT
    - 不因单帧肩/髋关键点抖动而频繁切换
    - FRONT 与 SIDE 都需要连续稳定若干帧才确认
    """

    def __init__(self):
        self.current_view = "CALIBRATING"

        self.candidate_view = None
        self.candidate_frames = 0
        self.transition_frames = 0

        self.ratio_buffer = deque(maxlen=7)
        self.smoothed_ratio = 0.0
        self.raw_ratio = 0.0

        # 实测：
        # 正面约 0.56
        # 完全侧面约 0.10
        #
        # 之前 FRONT >= 0.42 太宽松，
        # 身体仍处于斜向时就可能提前进入 FRONT。
        # 现在收紧到：
        # SIDE <= 0.18
        # FRONT >= 0.50
        # 中间全部作为 TRANSITION。
        self.side_threshold = 0.18
        self.front_threshold = 0.50

        # 转身只要连续几帧落入中间区，
        # 就先进入 TRANSITION，避免继续显示旧视角。
        self.transition_required_frames = 4

        # 从 TRANSITION 进入稳定 FRONT / SIDE
        # 需要更长时间确认。
        self.confirm_required_frames = 18

        # 初次启动允许稍快完成校准。
        self.initial_required_frames = 10

    def distance(
        self,
        point_a,
        point_b,
        aspect_ratio
    ):
        dx = (
            point_a[0]
            - point_b[0]
        ) * aspect_ratio

        dy = (
            point_a[1]
            - point_b[1]
        )

        return math.sqrt(
            dx * dx
            + dy * dy
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
            / frame_height
        )

        shoulder_width = self.distance(
            left_shoulder,
            right_shoulder,
            aspect_ratio
        )

        hip_width = self.distance(
            left_hip,
            right_hip,
            aspect_ratio
        )

        left_torso = self.distance(
            left_shoulder,
            left_hip,
            aspect_ratio
        )

        right_torso = self.distance(
            right_shoulder,
            right_hip,
            aspect_ratio
        )

        average_body_width = (
            shoulder_width
            + hip_width
        ) / 2

        average_torso_length = (
            left_torso
            + right_torso
        ) / 2

        if average_torso_length < 0.001:
            return 0.0

        return (
            average_body_width
            / average_torso_length
        )

    def classify_raw_view(
        self,
        ratio
    ):
        if ratio <= self.side_threshold:
            return "SIDE"

        if ratio >= self.front_threshold:
            return "FRONT"

        return "TRANSITION"

    def update_from_ratio(
        self,
        ratio,
        freeze=False
    ):
        self.raw_ratio = ratio

        self.ratio_buffer.append(
            ratio
        )

        self.smoothed_ratio = median(
            self.ratio_buffer
        )

        raw_view = self.classify_raw_view(
            self.smoothed_ratio
        )

        if freeze:
            return (
                self.current_view,
                self.smoothed_ratio,
                raw_view
            )

        if raw_view == "TRANSITION":
            self.candidate_view = None
            self.candidate_frames = 0
            self.transition_frames += 1

            if (
                self.transition_frames
                >= self.transition_required_frames
            ):
                self.current_view = "TRANSITION"

            return (
                self.current_view,
                self.smoothed_ratio,
                raw_view
            )

        self.transition_frames = 0

        if raw_view == self.candidate_view:
            self.candidate_frames += 1
        else:
            self.candidate_view = raw_view
            self.candidate_frames = 1

        required_frames = (
            self.initial_required_frames
            if self.current_view == "CALIBRATING"
            else self.confirm_required_frames
        )

        if (
            self.candidate_frames
            >= required_frames
        ):
            self.current_view = raw_view
            self.candidate_view = None
            self.candidate_frames = 0

        return (
            self.current_view,
            self.smoothed_ratio,
            raw_view
        )

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
        ratio = self.calculate_view_ratio(
            left_shoulder,
            right_shoulder,
            left_hip,
            right_hip,
            frame_width,
            frame_height
        )

        return self.update_from_ratio(
            ratio,
            freeze=freeze
        )

    def reset(self):
        self.current_view = "CALIBRATING"
        self.candidate_view = None
        self.candidate_frames = 0
        self.transition_frames = 0

        self.ratio_buffer.clear()

        self.smoothed_ratio = 0.0
        self.raw_ratio = 0.0
