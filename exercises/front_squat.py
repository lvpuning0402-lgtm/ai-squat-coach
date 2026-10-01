from collections import deque
from statistics import median

from pose.angles import calculate_angle


class FrontSquatAnalyzer:
    def __init__(self):
        # =====================================
        # 动作状态
        # =====================================

        self.stage = "CALIBRATING"

        self.count = 0

        self.down_frames = 0
        self.up_frames = 0

        self.required_frames = 6

        self.rep_started = False

        # =====================================
        # 站立基准
        # =====================================

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_body_height = None

        # =====================================
        # 基准更新速度
        # =====================================

        self.baseline_alpha = 0.05

        # =====================================
        # 下蹲阈值
        #
        # 都按身体高度归一化
        # =====================================

        self.shoulder_down_threshold = 0.11

        self.hip_down_threshold = 0.10

        self.up_threshold = 0.045

        # =====================================
        # 平滑
        # =====================================

        self.shoulder_descent_buffer = deque(
            maxlen=7
        )

        self.hip_descent_buffer = deque(
            maxlen=7
        )

        # =====================================
        # 头部中线偏移
        # =====================================

        self.head_shift_buffer = deque(
            maxlen=7
        )

        # =====================================
        # 肩膀高低差
        # =====================================

        self.shoulder_tilt_buffer = deque(
            maxlen=7
        )

    def midpoint(
        self,
        a,
        b
    ):
        return (
            (a[0] + b[0]) / 2,
            (a[1] + b[1]) / 2
        )

    def update_baseline(
        self,
        shoulder_y,
        hip_y,
        body_height
    ):
        if self.baseline_shoulder_y is None:

            self.baseline_shoulder_y = shoulder_y
            self.baseline_hip_y = hip_y
            self.baseline_body_height = body_height

            self.stage = "up"

            return

        alpha = self.baseline_alpha

        self.baseline_shoulder_y = (
            self.baseline_shoulder_y
            +
            alpha
            *
            (
                shoulder_y
                -
                self.baseline_shoulder_y
            )
        )

        self.baseline_hip_y = (
            self.baseline_hip_y
            +
            alpha
            *
            (
                hip_y
                -
                self.baseline_hip_y
            )
        )

        self.baseline_body_height = (
            self.baseline_body_height
            +
            alpha
            *
            (
                body_height
                -
                self.baseline_body_height
            )
        )

    def analyze(
        self,
        nose,
        left_shoulder,
        right_shoulder,
        left_hip,
        right_hip,
        left_knee,
        right_knee,
        left_ankle,
        right_ankle
    ):
        # =====================================
        # 中心点
        # =====================================

        shoulder_center = self.midpoint(
            left_shoulder,
            right_shoulder
        )

        hip_center = self.midpoint(
            left_hip,
            right_hip
        )

        ankle_center = self.midpoint(
            left_ankle,
            right_ankle
        )

        # =====================================
        # 当前身体高度
        # =====================================

        body_height = abs(
            ankle_center[1]
            -
            shoulder_center[1]
        )

        if body_height < 0.05:

            return None

        # =====================================
        # 初始校准
        # =====================================

        if self.baseline_shoulder_y is None:

            self.update_baseline(
                shoulder_center[1],
                hip_center[1],
                body_height
            )

        # =====================================
        # 归一化下降量
        # =====================================

        baseline_height = max(
            self.baseline_body_height,
            0.05
        )

        shoulder_descent = (
            shoulder_center[1]
            -
            self.baseline_shoulder_y
        ) / baseline_height

        hip_descent = (
            hip_center[1]
            -
            self.baseline_hip_y
        ) / baseline_height

        self.shoulder_descent_buffer.append(
            shoulder_descent
        )

        self.hip_descent_buffer.append(
            hip_descent
        )

        smooth_shoulder_descent = median(
            self.shoulder_descent_buffer
        )

        smooth_hip_descent = median(
            self.hip_descent_buffer
        )

        # =====================================
        # 双膝角
        #
        # 正面不把它作为核心状态判断，
        # 只作为辅助信号
        # =====================================

        left_knee_angle = calculate_angle(
            left_hip,
            left_knee,
            left_ankle
        )

        right_knee_angle = calculate_angle(
            right_hip,
            right_knee,
            right_ankle
        )

        average_knee_angle = (
            left_knee_angle
            +
            right_knee_angle
        ) / 2

        knee_bent = (
            average_knee_angle
            <
            165
        )

        # =====================================
        # FRONT DOWN 判断
        #
        # 肩 / 髋至少一个明显下降
        # 同时膝盖出现一定屈曲
        # =====================================

        down_signal = (
            (
                smooth_shoulder_descent
                >
                self.shoulder_down_threshold
            )
            or
            (
                smooth_hip_descent
                >
                self.hip_down_threshold
            )
        ) and knee_bent

        # =====================================
        # UP 判断
        # =====================================

        up_signal = (
            smooth_shoulder_descent
            <
            self.up_threshold
            and
            smooth_hip_descent
            <
            self.up_threshold
        )

        rep_completed = False

        # =====================================
        # DOWN
        # =====================================

        if down_signal:

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

        # =====================================
        # UP
        # =====================================

        elif up_signal:

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

                # 只有稳定站立时更新基准
                self.update_baseline(
                    shoulder_center[1],
                    hip_center[1],
                    body_height
                )

        else:

            self.down_frames = 0

            self.up_frames = 0

        # =====================================
        # 头部中线偏移
        #
        # 相对肩宽归一化
        # =====================================

        shoulder_width = abs(
            right_shoulder[0]
            -
            left_shoulder[0]
        )

        shoulder_width = max(
            shoulder_width,
            0.01
        )

        head_shift = abs(
            nose[0]
            -
            shoulder_center[0]
        ) / shoulder_width

        self.head_shift_buffer.append(
            head_shift
        )

        smooth_head_shift = median(
            self.head_shift_buffer
        )

        # =====================================
        # 肩膀高低差
        # =====================================

        shoulder_tilt = abs(
            left_shoulder[1]
            -
            right_shoulder[1]
        ) / shoulder_width

        self.shoulder_tilt_buffer.append(
            shoulder_tilt
        )

        smooth_shoulder_tilt = median(
            self.shoulder_tilt_buffer
        )

        return {
            "count":
                self.count,

            "stage":
                self.stage,

            "rep_completed":
                rep_completed,

            "shoulder_descent":
                smooth_shoulder_descent,

            "hip_descent":
                smooth_hip_descent,

            "average_knee_angle":
                average_knee_angle,

            "head_shift":
                smooth_head_shift,

            "shoulder_tilt":
                smooth_shoulder_tilt
        }

    def reset(
        self
    ):
        self.stage = "CALIBRATING"

        self.down_frames = 0

        self.up_frames = 0

        self.rep_started = False

        self.baseline_shoulder_y = None

        self.baseline_hip_y = None

        self.baseline_body_height = None

        self.shoulder_descent_buffer.clear()

        self.hip_descent_buffer.clear()

        self.head_shift_buffer.clear()

        self.shoulder_tilt_buffer.clear()