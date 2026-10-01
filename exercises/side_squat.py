from collections import deque
from statistics import median
import math
import time

from pose.angles import calculate_angle


class SideSquatAnalyzer:
    """
    侧面深蹲主分析器。

    侧面是主要技术分析视角，负责：
    - 多阶段动作识别
    - 膝角 / 髋角
    - 深度与 ROM
    - 躯干前倾
    - 头部前伸
    - 肩髋同步
    - 动作节奏
    """

    def __init__(self):
        self.phase = "STANDING"
        self.count = 0

        self.knee_buffer = deque(maxlen=7)
        self.hip_buffer = deque(maxlen=7)
        self.trunk_buffer = deque(maxlen=9)
        self.head_buffer = deque(maxlen=9)
        self.knee_velocity_buffer = deque(maxlen=5)
        self.sync_buffer = deque(maxlen=7)

        self.previous_knee_angle = 180.0

        self.phase_confirm_frames = 3
        self.standing_confirm_frames = 6

        self.descending_frames = 0
        self.bottom_frames = 0
        self.ascending_frames = 0
        self.standing_frames = 0

        self.start_angle = 155.0
        self.bottom_angle = 120.0
        self.standing_angle = 155.0

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_torso_length = None
        self.baseline_alpha = 0.04

        self.rep_start_time = None
        self.descent_start_time = None
        self.bottom_start_time = None
        self.ascent_start_time = None

        self.current_min_knee_angle = 180.0
        self.current_min_hip_angle = 180.0
        self.current_max_trunk_lean = 0.0
        self.current_max_head_forward = 0.0
        self.current_max_sync_error = 0.0

        self.last_rep = None

    @staticmethod
    def calculate_trunk_lean(
        shoulder,
        hip
    ):
        dx = abs(
            shoulder[0] - hip[0]
        )
        dy = abs(
            shoulder[1] - hip[1]
        )

        if dy < 0.001:
            return 90.0

        return math.degrees(
            math.atan2(
                dx,
                dy
            )
        )

    def update_baseline(
        self,
        shoulder,
        hip
    ):
        torso_length = max(
            math.dist(
                shoulder,
                hip
            ),
            0.01
        )

        if self.baseline_shoulder_y is None:
            self.baseline_shoulder_y = shoulder[1]
            self.baseline_hip_y = hip[1]
            self.baseline_torso_length = torso_length
            return

        alpha = self.baseline_alpha

        self.baseline_shoulder_y += alpha * (
            shoulder[1] - self.baseline_shoulder_y
        )
        self.baseline_hip_y += alpha * (
            hip[1] - self.baseline_hip_y
        )
        self.baseline_torso_length += alpha * (
            torso_length - self.baseline_torso_length
        )

    def reset_rep_metrics(self):
        self.rep_start_time = None
        self.descent_start_time = None
        self.bottom_start_time = None
        self.ascent_start_time = None

        self.current_min_knee_angle = 180.0
        self.current_min_hip_angle = 180.0
        self.current_max_trunk_lean = 0.0
        self.current_max_head_forward = 0.0
        self.current_max_sync_error = 0.0

    def complete_rep(self, now):
        descent_time = None
        bottom_time = None
        ascent_time = None
        total_time = None

        if self.descent_start_time is not None and self.bottom_start_time is not None:
            descent_time = self.bottom_start_time - self.descent_start_time

        if self.bottom_start_time is not None and self.ascent_start_time is not None:
            bottom_time = self.ascent_start_time - self.bottom_start_time

        if self.ascent_start_time is not None:
            ascent_time = now - self.ascent_start_time

        if self.rep_start_time is not None:
            total_time = now - self.rep_start_time

        rom_degrees = max(
            0.0,
            180.0 - self.current_min_knee_angle
        )

        self.last_rep = {
            "rep": self.count,
            "view": "SIDE",
            "descent_time": descent_time,
            "bottom_time": bottom_time,
            "ascent_time": ascent_time,
            "total_time": total_time,
            "rom_degrees": rom_degrees,
            "min_knee_angle": self.current_min_knee_angle,
            "min_hip_angle": self.current_min_hip_angle,
            "max_trunk_lean": self.current_max_trunk_lean,
            "max_head_forward": self.current_max_head_forward,
            "max_sync_error": self.current_max_sync_error
        }

        result = self.last_rep
        self.reset_rep_metrics()
        return result

    def analyze(
        self,
        nose,
        shoulder,
        hip,
        knee,
        ankle
    ):
        now = time.perf_counter()

        knee_angle = calculate_angle(
            hip,
            knee,
            ankle
        )
        hip_angle = calculate_angle(
            shoulder,
            hip,
            knee
        )

        self.knee_buffer.append(
            knee_angle
        )
        self.hip_buffer.append(
            hip_angle
        )

        smooth_knee = median(
            self.knee_buffer
        )
        smooth_hip = median(
            self.hip_buffer
        )

        trunk_lean = self.calculate_trunk_lean(
            shoulder,
            hip
        )
        self.trunk_buffer.append(
            trunk_lean
        )
        smooth_trunk = median(
            self.trunk_buffer
        )

        torso_length = max(
            math.dist(
                shoulder,
                hip
            ),
            0.01
        )

        head_forward = abs(
            nose[0] - shoulder[0]
        ) / torso_length

        self.head_buffer.append(
            head_forward
        )
        smooth_head = median(
            self.head_buffer
        )

        if self.baseline_shoulder_y is None:
            self.update_baseline(
                shoulder,
                hip
            )

        baseline_length = max(
            self.baseline_torso_length,
            0.01
        )

        shoulder_descent = (
            shoulder[1]
            - self.baseline_shoulder_y
        ) / baseline_length

        hip_descent = (
            hip[1]
            - self.baseline_hip_y
        ) / baseline_length

        sync_error = abs(
            shoulder_descent
            - hip_descent
        )

        self.sync_buffer.append(
            sync_error
        )
        smooth_sync = median(
            self.sync_buffer
        )

        knee_velocity = (
            smooth_knee
            - self.previous_knee_angle
        )
        self.previous_knee_angle = smooth_knee

        self.knee_velocity_buffer.append(
            knee_velocity
        )
        smooth_knee_velocity = median(
            self.knee_velocity_buffer
        )

        rep_completed = False
        rep_summary = None

        if self.phase == "STANDING":
            self.update_baseline(
                shoulder,
                hip
            )

            if (
                smooth_knee < self.start_angle
                and smooth_knee_velocity < -0.15
            ):
                self.descending_frames += 1
            else:
                self.descending_frames = 0

            if self.descending_frames >= self.phase_confirm_frames:
                self.phase = "DESCENDING"
                self.rep_start_time = now
                self.descent_start_time = now
                self.current_min_knee_angle = smooth_knee
                self.current_min_hip_angle = smooth_hip

        elif self.phase == "DESCENDING":
            bottom_signal = (
                smooth_knee < self.bottom_angle
                and (
                    abs(smooth_knee_velocity) < 0.30
                    or smooth_knee_velocity > 0.10
                )
            )

            if bottom_signal:
                self.bottom_frames += 1
            else:
                self.bottom_frames = 0

            if self.bottom_frames >= self.phase_confirm_frames:
                self.phase = "BOTTOM"
                self.bottom_start_time = now

        elif self.phase == "BOTTOM":
            if smooth_knee_velocity > 0.15:
                self.ascending_frames += 1
            else:
                self.ascending_frames = 0

            if self.ascending_frames >= self.phase_confirm_frames:
                self.phase = "ASCENDING"
                self.ascent_start_time = now

        elif self.phase == "ASCENDING":
            if smooth_knee > self.standing_angle:
                self.standing_frames += 1
            else:
                self.standing_frames = 0

            if self.standing_frames >= self.standing_confirm_frames:
                self.phase = "STANDING"
                self.count += 1
                rep_completed = True
                rep_summary = self.complete_rep(
                    now
                )

                self.descending_frames = 0
                self.bottom_frames = 0
                self.ascending_frames = 0
                self.standing_frames = 0

        if self.phase != "STANDING":
            self.current_min_knee_angle = min(
                self.current_min_knee_angle,
                smooth_knee
            )
            self.current_min_hip_angle = min(
                self.current_min_hip_angle,
                smooth_hip
            )
            self.current_max_trunk_lean = max(
                self.current_max_trunk_lean,
                smooth_trunk
            )
            self.current_max_head_forward = max(
                self.current_max_head_forward,
                smooth_head
            )
            self.current_max_sync_error = max(
                self.current_max_sync_error,
                smooth_sync
            )

        if smooth_knee > 150:
            depth = "READY"
        elif smooth_knee > 120:
            depth = "GO DEEPER"
        elif smooth_knee >= 85:
            depth = "GOOD DEPTH"
        else:
            depth = "VERY DEEP"

        phase_elapsed = 0.0
        if self.rep_start_time is not None:
            phase_elapsed = now - self.rep_start_time

        return {
            "count": self.count,
            "stage": self.phase,
            "phase": self.phase,
            "rep_completed": rep_completed,
            "rep_summary": rep_summary,
            "knee_angle": smooth_knee,
            "hip_angle": smooth_hip,
            "trunk_lean": smooth_trunk,
            "head_forward": smooth_head,
            "shoulder_hip_sync": smooth_sync,
            "knee_velocity": smooth_knee_velocity,
            "rom_degrees": max(
                0.0,
                180.0 - self.current_min_knee_angle
            ),
            "phase_elapsed": phase_elapsed,
            "depth": depth,
            "last_rep": self.last_rep
        }

    def reset(self):
        self.phase = "STANDING"

        self.descending_frames = 0
        self.bottom_frames = 0
        self.ascending_frames = 0
        self.standing_frames = 0

        self.knee_buffer.clear()
        self.hip_buffer.clear()
        self.trunk_buffer.clear()
        self.head_buffer.clear()
        self.knee_velocity_buffer.clear()
        self.sync_buffer.clear()

        self.previous_knee_angle = 180.0

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_torso_length = None

        self.reset_rep_metrics()
