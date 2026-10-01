from collections import deque
from statistics import median

from pose.angles import calculate_angle


class SideSquatAnalyzer:
    def __init__(self):
        # =====================================
        # 状态
        # =====================================

        self.stage = "unknown"

        self.count = 0

        self.down_frames = 0

        self.up_frames = 0

        self.required_frames = 7

        self.rep_started = False

        # =====================================
        # 阈值
        # =====================================

        self.down_threshold = 120

        self.up_threshold = 155

        # =====================================
        # 角度缓冲
        # =====================================

        self.knee_buffer = deque(
            maxlen=7
        )

        self.hip_buffer = deque(
            maxlen=7
        )

        self.trunk_buffer = deque(
            maxlen=9
        )

        self.head_buffer = deque(
            maxlen=9
        )

    def calculate_trunk_lean(
        self,
        shoulder,
        hip
    ):
        dx = abs(
            shoulder[0]
            -
            hip[0]
        )

        dy = abs(
            shoulder[1]
            -
            hip[1]
        )

        if dy < 0.001:
            return 90.0

        import math

        return math.degrees(
            math.atan2(
                dx,
                dy
            )
        )

    def analyze(
        self,
        nose,
        shoulder,
        hip,
        knee,
        ankle
    ):
        # =====================================
        # 膝角
        # =====================================

        knee_angle = calculate_angle(
            hip,
            knee,
            ankle
        )

        self.knee_buffer.append(
            knee_angle
        )

        smooth_knee = median(
            self.knee_buffer
        )

        # =====================================
        # 髋角
        #
        # shoulder - hip - knee
        # =====================================

        hip_angle = calculate_angle(
            shoulder,
            hip,
            knee
        )

        self.hip_buffer.append(
            hip_angle
        )

        smooth_hip = median(
            self.hip_buffer
        )

        # =====================================
        # 躯干前倾
        # =====================================

        trunk_lean = (
            self.calculate_trunk_lean(
                shoulder,
                hip
            )
        )

        self.trunk_buffer.append(
            trunk_lean
        )

        smooth_trunk = median(
            self.trunk_buffer
        )

        # =====================================
        # 头部相对肩膀位置
        #
        # 按躯干长度归一化
        # =====================================

        torso_length = (
            (
                (
                    shoulder[0]
                    -
                    hip[0]
                ) ** 2
                +
                (
                    shoulder[1]
                    -
                    hip[1]
                ) ** 2
            )
            ** 0.5
        )

        torso_length = max(
            torso_length,
            0.01
        )

        head_forward = abs(
            nose[0]
            -
            shoulder[0]
        ) / torso_length

        self.head_buffer.append(
            head_forward
        )

        smooth_head = median(
            self.head_buffer
        )

        # =====================================
        # 动作阶段
        # =====================================

        rep_completed = False

        if (
            smooth_knee
            <
            self.down_threshold
        ):

            self.down_frames += 1

            self.up_frames = 0

            if (
                self.down_frames
                >=
                self.required_frames
            ):

                if self.stage == "up":

                    self.stage = "down"

                    self.rep_started = True

        elif (
            smooth_knee
            >
            self.up_threshold
        ):

            self.up_frames += 1

            self.down_frames = 0

            if (
                self.up_frames
                >=
                self.required_frames
            ):

                if (
                    self.stage == "down"
                    and
                    self.rep_started
                ):

                    self.count += 1

                    rep_completed = True

                    self.rep_started = False

                self.stage = "up"

        else:

            self.down_frames = 0

            self.up_frames = 0

        # =====================================
        # 深度
        # =====================================

        if smooth_knee > 150:

            depth = "READY"

        elif smooth_knee > 120:

            depth = "GO DEEPER"

        elif smooth_knee >= 85:

            depth = "GOOD DEPTH"

        else:

            depth = "VERY DEEP"

        return {
            "count":
                self.count,

            "stage":
                self.stage,

            "rep_completed":
                rep_completed,

            "knee_angle":
                smooth_knee,

            "hip_angle":
                smooth_hip,

            "trunk_lean":
                smooth_trunk,

            "head_forward":
                smooth_head,

            "depth":
                depth
        }

    def reset(
        self
    ):
        self.stage = "unknown"

        self.down_frames = 0

        self.up_frames = 0

        self.rep_started = False

        self.knee_buffer.clear()

        self.hip_buffer.clear()

        self.trunk_buffer.clear()

        self.head_buffer.clear()