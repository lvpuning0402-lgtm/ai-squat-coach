from collections import deque
from statistics import median
import time

from pose.angles import calculate_angle


class FrontSquatAnalyzer:
    """
    正面深蹲分析器。

    核心原则：
    1. 不依赖单一膝角判断是否下蹲。
    2. 主要使用肩部/髋部整体下降。
    3. 膝角只作为辅助信号。
    4. 使用多阶段状态机：
       STANDING -> DESCENDING -> BOTTOM -> ASCENDING -> STANDING
    5. 同时记录节奏、ROM、头部稳定、肩部水平和肩髋同步。
    6. 当用户在测试过程中重新站位、远近变化或中途取消动作时，
       自动恢复到新的站立基准，避免状态机卡死。
    """

    def __init__(self):
        self.phase = "STANDING"
        self.count = 0

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_body_height = None
        self.baseline_shoulder_x = None
        self.baseline_alpha = 0.04

        self.shoulder_buffer = deque(maxlen=7)
        self.hip_buffer = deque(maxlen=7)
        self.combined_buffer = deque(maxlen=7)
        self.velocity_buffer = deque(maxlen=5)
        self.head_shift_buffer = deque(maxlen=7)
        self.shoulder_tilt_buffer = deque(maxlen=7)
        self.center_shift_buffer = deque(maxlen=7)

        self.previous_descent = 0.0

        self.start_descent_threshold = 0.045
        self.bottom_depth_threshold = 0.105
        self.standing_threshold = 0.050

        self.phase_confirm_frames = 3
        self.standing_confirm_frames = 6
        self.abort_confirm_frames = 6

        self.descending_frames = 0
        self.bottom_frames = 0
        self.ascending_frames = 0
        self.standing_frames = 0
        self.abort_frames = 0

        # 站立状态下如果出现这些极端变化，
        # 视为用户重新站位 / 摄像头基准失效，而不是动作质量问题。
        self.reanchor_negative_descent = -0.18
        self.reanchor_center_shift = 1.25
        self.reanchor_scale_low = 0.70
        self.reanchor_scale_high = 1.35

        self.rep_start_time = None
        self.descent_start_time = None
        self.bottom_start_time = None
        self.ascent_start_time = None

        self.current_max_descent = 0.0
        self.current_max_head_shift = 0.0
        self.current_max_shoulder_tilt = 0.0
        self.current_max_center_shift = 0.0
        self.current_max_sync_error = 0.0
        self.current_max_ascent_sync_error = 0.0
        self.ascent_start_shoulder_descent = None
        self.ascent_start_hip_descent = None
        self.ascent_sync_buffer = deque(maxlen=5)
        self.current_min_knee_angle = 180.0

        self.last_rep = None

    @staticmethod
    def midpoint(a, b):
        return (
            (a[0] + b[0]) / 2,
            (a[1] + b[1]) / 2
        )

    def update_baseline(
        self,
        shoulder_center,
        hip_center,
        body_height
    ):
        if self.baseline_shoulder_y is None:
            self.baseline_shoulder_y = shoulder_center[1]
            self.baseline_hip_y = hip_center[1]
            self.baseline_body_height = body_height
            self.baseline_shoulder_x = shoulder_center[0]
            return

        alpha = self.baseline_alpha

        self.baseline_shoulder_y += alpha * (
            shoulder_center[1]
            - self.baseline_shoulder_y
        )
        self.baseline_hip_y += alpha * (
            hip_center[1]
            - self.baseline_hip_y
        )
        self.baseline_body_height += alpha * (
            body_height
            - self.baseline_body_height
        )
        self.baseline_shoulder_x += alpha * (
            shoulder_center[0]
            - self.baseline_shoulder_x
        )

    def reset_phase_counters(self):
        self.descending_frames = 0
        self.bottom_frames = 0
        self.ascending_frames = 0
        self.standing_frames = 0
        self.abort_frames = 0

    def reset_rep_metrics(self):
        self.rep_start_time = None
        self.descent_start_time = None
        self.bottom_start_time = None
        self.ascent_start_time = None

        self.current_max_descent = 0.0
        self.current_max_head_shift = 0.0
        self.current_max_shoulder_tilt = 0.0
        self.current_max_center_shift = 0.0
        self.current_max_sync_error = 0.0
        self.current_max_ascent_sync_error = 0.0
        self.ascent_start_shoulder_descent = None
        self.ascent_start_hip_descent = None
        self.ascent_sync_buffer.clear()
        self.current_min_knee_angle = 180.0

    def clear_motion_buffers(self):
        self.shoulder_buffer.clear()
        self.hip_buffer.clear()
        self.combined_buffer.clear()
        self.velocity_buffer.clear()
        self.center_shift_buffer.clear()
        self.ascent_sync_buffer.clear()

        self.previous_descent = 0.0

    def reanchor_baseline(
        self,
        shoulder_center,
        hip_center,
        body_height
    ):
        """
        重新建立当前站立基准。

        用于：
        - 用户从近处走到远处
        - 用户横向重新站位
        - 动作中途取消后重新站直
        - 初始基准被遮挡/跳点污染
        """
        self.phase = "STANDING"
        self.reset_phase_counters()
        self.reset_rep_metrics()
        self.clear_motion_buffers()

        self.baseline_shoulder_y = shoulder_center[1]
        self.baseline_hip_y = hip_center[1]
        self.baseline_body_height = max(
            body_height,
            0.05
        )
        self.baseline_shoulder_x = shoulder_center[0]

    def complete_rep(self, now):
        descent_time = None
        bottom_time = None
        ascent_time = None
        total_time = None

        if (
            self.descent_start_time is not None
            and self.bottom_start_time is not None
        ):
            descent_time = (
                self.bottom_start_time
                - self.descent_start_time
            )

        if (
            self.bottom_start_time is not None
            and self.ascent_start_time is not None
        ):
            bottom_time = (
                self.ascent_start_time
                - self.bottom_start_time
            )

        if self.ascent_start_time is not None:
            ascent_time = (
                now
                - self.ascent_start_time
            )

        if self.rep_start_time is not None:
            total_time = (
                now
                - self.rep_start_time
            )

        self.last_rep = {
            "rep": self.count,
            "view": "FRONT",
            "descent_time": descent_time,
            "bottom_time": bottom_time,
            "ascent_time": ascent_time,
            "total_time": total_time,
            "rom": self.current_max_descent,
            "min_knee_angle": self.current_min_knee_angle,
            "max_head_shift": self.current_max_head_shift,
            "max_shoulder_tilt": self.current_max_shoulder_tilt,
            "max_center_shift": self.current_max_center_shift,
            "max_sync_error": self.current_max_sync_error,
            "max_ascent_sync_error": self.current_max_ascent_sync_error
        }

        result = self.last_rep
        self.reset_rep_metrics()

        return result

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
        now = time.perf_counter()

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

        body_height = abs(
            ankle_center[1]
            - shoulder_center[1]
        )

        if body_height < 0.05:
            return None

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
            + right_knee_angle
        ) / 2

        standing_like = (
            average_knee_angle
            >= 165.0
        )

        shoulder_width = max(
            abs(
                right_shoulder[0]
                - left_shoulder[0]
            ),
            0.01
        )

        head_shift = abs(
            nose[0]
            - shoulder_center[0]
        ) / shoulder_width

        shoulder_tilt = abs(
            left_shoulder[1]
            - right_shoulder[1]
        ) / shoulder_width

        self.head_shift_buffer.append(
            head_shift
        )
        self.shoulder_tilt_buffer.append(
            shoulder_tilt
        )

        smooth_head_shift = median(
            self.head_shift_buffer
        )
        smooth_shoulder_tilt = median(
            self.shoulder_tilt_buffer
        )

        if self.baseline_shoulder_y is None:
            self.reanchor_baseline(
                shoulder_center,
                hip_center,
                body_height
            )

        baseline_height = max(
            self.baseline_body_height,
            0.05
        )

        shoulder_descent = (
            shoulder_center[1]
            - self.baseline_shoulder_y
        ) / baseline_height

        hip_descent = (
            hip_center[1]
            - self.baseline_hip_y
        ) / baseline_height

        self.shoulder_buffer.append(
            shoulder_descent
        )
        self.hip_buffer.append(
            hip_descent
        )

        smooth_shoulder_descent = median(
            self.shoulder_buffer
        )
        smooth_hip_descent = median(
            self.hip_buffer
        )

        combined_descent = (
            0.65
            * smooth_shoulder_descent
            + 0.35
            * smooth_hip_descent
        )

        self.combined_buffer.append(
            combined_descent
        )

        smooth_descent = median(
            self.combined_buffer
        )

        velocity = (
            smooth_descent
            - self.previous_descent
        )

        self.previous_descent = (
            smooth_descent
        )

        self.velocity_buffer.append(
            velocity
        )

        smooth_velocity = median(
            self.velocity_buffer
        )

        center_shift = abs(
            shoulder_center[0]
            - self.baseline_shoulder_x
        ) / shoulder_width

        self.center_shift_buffer.append(
            center_shift
        )

        smooth_center_shift = median(
            self.center_shift_buffer
        )

        sync_error = abs(
            smooth_shoulder_descent
            - smooth_hip_descent
        )

        scale_ratio = (
            body_height
            / baseline_height
        )

        rep_completed = False
        rep_summary = None
        rep_aborted = False
        baseline_reset = False

        # 用户已明显站直，但相对旧基准出现不可能的大幅上移、
        # 横向变化或身体尺度变化时，直接重新校准。
        baseline_mismatch = (
            standing_like
            and (
                smooth_descent
                < self.reanchor_negative_descent
                or smooth_center_shift
                > self.reanchor_center_shift
                or scale_ratio
                < self.reanchor_scale_low
                or scale_ratio
                > self.reanchor_scale_high
            )
        )

        if baseline_mismatch:
            rep_aborted = (
                self.phase
                != "STANDING"
            )
            baseline_reset = True

            self.reanchor_baseline(
                shoulder_center,
                hip_center,
                body_height
            )

            smooth_shoulder_descent = 0.0
            smooth_hip_descent = 0.0
            smooth_descent = 0.0
            smooth_velocity = 0.0
            smooth_center_shift = 0.0
            sync_error = 0.0
            scale_ratio = 1.0

        knee_bent = (
            average_knee_angle
            < 168.0
        )

        if not baseline_reset:
            if self.phase == "STANDING":
                self.update_baseline(
                    shoulder_center,
                    hip_center,
                    body_height
                )

                start_signal = (
                    smooth_descent
                    > self.start_descent_threshold
                    and knee_bent
                    and smooth_velocity
                    > 0.0005
                )

                if start_signal:
                    self.descending_frames += 1
                else:
                    self.descending_frames = 0

                if (
                    self.descending_frames
                    >= self.phase_confirm_frames
                ):
                    self.phase = "DESCENDING"
                    self.rep_start_time = now
                    self.descent_start_time = now
                    self.current_max_descent = (
                        smooth_descent
                    )

            elif self.phase == "DESCENDING":
                self.current_max_descent = max(
                    self.current_max_descent,
                    smooth_descent
                )

                returned_to_standing = (
                    standing_like
                    and smooth_descent
                    < (
                        self.standing_threshold
                        * 1.4
                    )
                )

                if returned_to_standing:
                    self.abort_frames += 1
                else:
                    self.abort_frames = 0

                if (
                    self.abort_frames
                    >= self.abort_confirm_frames
                ):
                    rep_aborted = True

                    self.reanchor_baseline(
                        shoulder_center,
                        hip_center,
                        body_height
                    )

                    smooth_shoulder_descent = 0.0
                    smooth_hip_descent = 0.0
                    smooth_descent = 0.0
                    smooth_velocity = 0.0
                    smooth_center_shift = 0.0
                    sync_error = 0.0

                else:
                    bottom_signal = (
                        smooth_descent
                        > self.bottom_depth_threshold
                        and (
                            abs(
                                smooth_velocity
                            )
                            < 0.0015
                            or smooth_velocity
                            < -0.0005
                        )
                    )

                    if bottom_signal:
                        self.bottom_frames += 1
                    else:
                        self.bottom_frames = 0

                    if (
                        self.bottom_frames
                        >= self.phase_confirm_frames
                    ):
                        self.phase = "BOTTOM"
                        self.bottom_start_time = now
                        self.abort_frames = 0

            elif self.phase == "BOTTOM":
                self.current_max_descent = max(
                    self.current_max_descent,
                    smooth_descent
                )

                if smooth_velocity < -0.0008:
                    self.ascending_frames += 1
                else:
                    self.ascending_frames = 0

                if (
                    self.ascending_frames
                    >= self.phase_confirm_frames
                ):
                    self.phase = "ASCENDING"
                    self.ascent_start_time = now
                    self.ascent_start_shoulder_descent = (
                        smooth_shoulder_descent
                    )
                    self.ascent_start_hip_descent = (
                        smooth_hip_descent
                    )
                    self.ascent_sync_buffer.clear()
                    self.abort_frames = 0

            elif self.phase == "ASCENDING":
                if (
                    self.ascent_start_shoulder_descent
                    is not None
                    and self.ascent_start_hip_descent
                    is not None
                ):
                    shoulder_range = max(
                        abs(
                            self.ascent_start_shoulder_descent
                        ),
                        0.02
                    )
                    hip_range = max(
                        abs(
                            self.ascent_start_hip_descent
                        ),
                        0.02
                    )

                    shoulder_progress = (
                        self.ascent_start_shoulder_descent
                        - smooth_shoulder_descent
                    ) / shoulder_range

                    hip_progress = (
                        self.ascent_start_hip_descent
                        - smooth_hip_descent
                    ) / hip_range

                    ascent_sync_error = abs(
                        shoulder_progress
                        - hip_progress
                    )

                    self.ascent_sync_buffer.append(
                        ascent_sync_error
                    )

                    smooth_ascent_sync = median(
                        self.ascent_sync_buffer
                    )

                    self.current_max_ascent_sync_error = max(
                        self.current_max_ascent_sync_error,
                        smooth_ascent_sync
                    )

                if (
                    smooth_descent
                    < self.standing_threshold
                    and standing_like
                ):
                    self.standing_frames += 1
                else:
                    self.standing_frames = 0

                if (
                    self.standing_frames
                    >= self.standing_confirm_frames
                ):
                    self.phase = "STANDING"
                    self.count += 1
                    rep_completed = True

                    rep_summary = self.complete_rep(
                        now
                    )

                    self.reset_phase_counters()

        if (
            self.phase
            != "STANDING"
            and not rep_aborted
        ):
            self.current_max_descent = max(
                self.current_max_descent,
                smooth_descent
            )
            self.current_max_head_shift = max(
                self.current_max_head_shift,
                smooth_head_shift
            )
            self.current_max_shoulder_tilt = max(
                self.current_max_shoulder_tilt,
                smooth_shoulder_tilt
            )
            self.current_max_center_shift = max(
                self.current_max_center_shift,
                smooth_center_shift
            )
            self.current_max_sync_error = max(
                self.current_max_sync_error,
                sync_error
            )
            self.current_min_knee_angle = min(
                self.current_min_knee_angle,
                average_knee_angle
            )

        phase_elapsed = 0.0

        if self.rep_start_time is not None:
            phase_elapsed = (
                now
                - self.rep_start_time
            )

        return {
            "count": self.count,
            "stage": self.phase,
            "phase": self.phase,
            "rep_completed": rep_completed,
            "rep_summary": rep_summary,
            "rep_aborted": rep_aborted,
            "baseline_reset": baseline_reset,
            "shoulder_descent": smooth_shoulder_descent,
            "hip_descent": smooth_hip_descent,
            "combined_descent": smooth_descent,
            "descent_velocity": smooth_velocity,
            "average_knee_angle": average_knee_angle,
            "head_shift": smooth_head_shift,
            "shoulder_tilt": smooth_shoulder_tilt,
            "center_shift": smooth_center_shift,
            "shoulder_hip_sync": sync_error,
            "ascent_sync_error": (
                median(
                    self.ascent_sync_buffer
                )
                if self.ascent_sync_buffer
                else None
            ),
            "body_scale_ratio": scale_ratio,
            "rom": self.current_max_descent,
            "phase_elapsed": phase_elapsed,
            "last_rep": self.last_rep
        }

    def reset(self):
        self.phase = "STANDING"

        self.reset_phase_counters()

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_body_height = None
        self.baseline_shoulder_x = None

        self.shoulder_buffer.clear()
        self.hip_buffer.clear()
        self.combined_buffer.clear()
        self.velocity_buffer.clear()
        self.head_shift_buffer.clear()
        self.shoulder_tilt_buffer.clear()
        self.center_shift_buffer.clear()

        self.previous_descent = 0.0

        self.reset_rep_metrics()
