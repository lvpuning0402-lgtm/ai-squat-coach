from collections import deque
from statistics import median
import math
import time

from pose.angles import calculate_angle
from standards.squat_standard import (
    DETECTION,
    VISION_TOLERANCE,
)


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
    - 重新站位后的基准恢复
    - 未完成动作的自动取消
    """

    def __init__(self):
        self.phase = "STANDING"
        self.count = 0

        self.knee_buffer = deque(maxlen=7)
        self.hip_buffer = deque(maxlen=7)
        self.trunk_buffer = deque(maxlen=9)
        self.head_buffer = deque(maxlen=9)
        self.shin_buffer = deque(maxlen=7)
        self.knee_velocity_buffer = deque(maxlen=5)
        self.sync_buffer = deque(maxlen=7)

        self.previous_knee_angle = 180.0

        self.phase_confirm_frames = 3
        self.standing_confirm_frames = 6
        self.abort_confirm_frames = 6

        self.descending_frames = 0
        self.bottom_frames = 0
        self.ascending_frames = 0
        self.standing_frames = 0
        self.abort_frames = 0

        # State-machine thresholds only. These detect motion phases;
        # they are not used as exercise-quality standards.
        self.start_angle = DETECTION[
            "side_start_knee_angle"
        ]
        self.bottom_angle = DETECTION[
            "side_bottom_knee_angle"
        ]
        self.standing_angle = DETECTION[
            "side_standing_knee_angle"
        ]
        self.standing_like_angle = DETECTION[
            "side_standing_like_angle"
        ]

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_torso_length = None
        self.baseline_alpha = 0.04

        # 站直时若相对旧基准发生很大位置或尺度变化，
        # 视为重新站位，而不是新的动作。
        self.reanchor_vertical_shift = 0.75
        self.reanchor_scale_low = 0.70
        self.reanchor_scale_high = 1.35

        self.rep_start_time = None
        self.descent_start_time = None
        self.bottom_start_time = None
        self.ascent_start_time = None

        self.current_min_knee_angle = 180.0
        self.current_min_hip_angle = 180.0
        self.current_max_knee_angle = 0.0
        self.current_shin_angle_at_min_knee = 0.0
        self.current_max_trunk_lean = 0.0
        self.current_max_head_forward = 0.0
        self.current_max_sync_error = 0.0
        self.current_max_ascent_sync_error = 0.0
        self.ascent_start_shoulder_descent = None
        self.ascent_start_hip_descent = None
        self.ascent_sync_buffer = deque(maxlen=5)
        self.current_max_depth_margin = -10.0
        self.phase_metrics = self._new_phase_metrics()

        self.last_rep = None

    @staticmethod
    def _new_phase_metrics():
        template = {
            "samples": 0,
            "min_knee_angle": 180.0,
            "min_hip_angle": 180.0,
            "max_knee_angle": 0.0,
            "min_trunk_lean": 90.0,
            "max_trunk_lean": 0.0,
            "min_shin_angle": 90.0,
            "max_shin_angle": 0.0,
            "max_head_forward": 0.0,
            "max_sync_error": 0.0,
            "max_ascent_sync_error": 0.0,
            "max_depth_margin": -10.0,
        }

        return {
            phase: dict(
                template
            )
            for phase in (
                "descent",
                "bottom",
                "ascent",
            )
        }

    @staticmethod
    def _phase_key(
        phase
    ):
        return {
            "DESCENDING": "descent",
            "BOTTOM": "bottom",
            "ASCENDING": "ascent",
        }.get(
            phase
        )

    def _record_phase_metrics(
        self,
        phase,
        knee_angle,
        hip_angle,
        trunk_lean,
        shin_angle,
        head_forward,
        sync_error,
        ascent_sync_error,
        depth_margin
    ):
        phase_key = self._phase_key(
            phase
        )

        if phase_key is None:
            return

        metrics = self.phase_metrics[
            phase_key
        ]

        metrics[
            "samples"
        ] += 1
        metrics[
            "min_knee_angle"
        ] = min(
            metrics[
                "min_knee_angle"
            ],
            knee_angle
        )
        metrics[
            "min_hip_angle"
        ] = min(
            metrics[
                "min_hip_angle"
            ],
            hip_angle
        )
        metrics[
            "max_knee_angle"
        ] = max(
            metrics[
                "max_knee_angle"
            ],
            knee_angle
        )
        metrics[
            "min_trunk_lean"
        ] = min(
            metrics[
                "min_trunk_lean"
            ],
            trunk_lean
        )
        metrics[
            "max_trunk_lean"
        ] = max(
            metrics[
                "max_trunk_lean"
            ],
            trunk_lean
        )
        metrics[
            "min_shin_angle"
        ] = min(
            metrics[
                "min_shin_angle"
            ],
            shin_angle
        )
        metrics[
            "max_shin_angle"
        ] = max(
            metrics[
                "max_shin_angle"
            ],
            shin_angle
        )
        metrics[
            "max_head_forward"
        ] = max(
            metrics[
                "max_head_forward"
            ],
            head_forward
        )
        metrics[
            "max_sync_error"
        ] = max(
            metrics[
                "max_sync_error"
            ],
            sync_error
        )
        metrics[
            "max_depth_margin"
        ] = max(
            metrics[
                "max_depth_margin"
            ],
            depth_margin
        )

        if ascent_sync_error is not None:
            metrics[
                "max_ascent_sync_error"
            ] = max(
                metrics[
                    "max_ascent_sync_error"
                ],
                ascent_sync_error
            )

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

    def reset_phase_counters(self):
        self.descending_frames = 0
        self.bottom_frames = 0
        self.ascending_frames = 0
        self.standing_frames = 0
        self.abort_frames = 0

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
            shoulder[1]
            - self.baseline_shoulder_y
        )
        self.baseline_hip_y += alpha * (
            hip[1]
            - self.baseline_hip_y
        )
        self.baseline_torso_length += alpha * (
            torso_length
            - self.baseline_torso_length
        )

    def clear_motion_buffers(self):
        self.knee_buffer.clear()
        self.hip_buffer.clear()
        self.trunk_buffer.clear()
        self.head_buffer.clear()
        self.shin_buffer.clear()
        self.knee_velocity_buffer.clear()
        self.sync_buffer.clear()
        self.ascent_sync_buffer.clear()

        self.previous_knee_angle = 180.0

    def reset_rep_metrics(self):
        self.rep_start_time = None
        self.descent_start_time = None
        self.bottom_start_time = None
        self.ascent_start_time = None

        self.current_min_knee_angle = 180.0
        self.current_min_hip_angle = 180.0
        self.current_max_knee_angle = 0.0
        self.current_shin_angle_at_min_knee = 0.0
        self.current_max_trunk_lean = 0.0
        self.current_max_head_forward = 0.0
        self.current_max_sync_error = 0.0
        self.current_max_ascent_sync_error = 0.0
        self.ascent_start_shoulder_descent = None
        self.ascent_start_hip_descent = None
        self.ascent_sync_buffer.clear()
        self.current_max_depth_margin = -10.0
        self.phase_metrics = self._new_phase_metrics()

    def reanchor_baseline(
        self,
        shoulder,
        hip
    ):
        """
        重新建立侧面站立基准。

        适用于：
        - 走近 / 走远后重新站好
        - 人在画面中上下重新站位
        - 未完成深蹲后重新站直
        - 切换跟踪腿后重新稳定
        """
        torso_length = max(
            math.dist(
                shoulder,
                hip
            ),
            0.01
        )

        self.phase = "STANDING"
        self.reset_phase_counters()
        self.reset_rep_metrics()
        self.clear_motion_buffers()

        self.baseline_shoulder_y = shoulder[1]
        self.baseline_hip_y = hip[1]
        self.baseline_torso_length = torso_length

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

        rom_degrees = max(
            0.0,
            180.0
            - self.current_min_knee_angle
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
            "max_knee_angle": self.current_max_knee_angle,
            "shin_angle_at_min_knee": (
                self.current_shin_angle_at_min_knee
            ),
            "max_trunk_lean": self.current_max_trunk_lean,
            "max_head_forward": self.current_max_head_forward,
            "max_sync_error": self.current_max_sync_error,
            "max_ascent_sync_error": self.current_max_ascent_sync_error,
            "max_depth_margin": self.current_max_depth_margin,
            "depth_standard_met": (
                self.current_max_depth_margin
                >= VISION_TOLERANCE[
                    "general_depth_margin_min"
                ]
            ),
            "ipf_depth_proxy_met": (
                self.current_max_depth_margin
                >= VISION_TOLERANCE[
                    "ipf_depth_margin_min"
                ]
            ),
            "phase_metrics": {
                phase: dict(
                    metrics
                )
                for phase, metrics
                in self.phase_metrics.items()
            }
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

        shin_dx = abs(
            knee[0]
            - ankle[0]
        )
        shin_dy = abs(
            knee[1]
            - ankle[1]
        )
        shin_angle = math.degrees(
            math.atan2(
                shin_dx,
                max(
                    shin_dy,
                    0.001
                )
            )
        )
        self.shin_buffer.append(
            shin_angle
        )
        smooth_shin_angle = median(
            self.shin_buffer
        )

        torso_length = max(
            math.dist(
                shoulder,
                hip
            ),
            0.01
        )

        thigh_length = max(
            math.dist(
                hip,
                knee
            ),
            0.01
        )

        # Standardized side-view depth proxy:
        # 0.0 means hip and knee landmarks are level.
        # Positive means the hip landmark is lower than the knee landmark.
        # This is a camera landmark proxy for parallel-or-below depth,
        # not an official IPF referee decision.
        depth_margin = (
            hip[1]
            - knee[1]
        ) / thigh_length

        head_forward = abs(
            nose[0]
            - shoulder[0]
        ) / torso_length

        self.head_buffer.append(
            head_forward
        )
        smooth_head = median(
            self.head_buffer
        )

        if self.baseline_shoulder_y is None:
            self.reanchor_baseline(
                shoulder,
                hip
            )

            # reanchor 会清空缓冲，因此把当前帧重新放回缓冲。
            self.knee_buffer.append(
                knee_angle
            )
            self.hip_buffer.append(
                hip_angle
            )
            self.trunk_buffer.append(
                trunk_lean
            )
            self.head_buffer.append(
                head_forward
            )
            self.shin_buffer.append(
                shin_angle
            )

            smooth_knee = knee_angle
            smooth_hip = hip_angle
            smooth_trunk = trunk_lean
            smooth_head = head_forward

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

        self.previous_knee_angle = (
            smooth_knee
        )

        self.knee_velocity_buffer.append(
            knee_velocity
        )

        smooth_knee_velocity = median(
            self.knee_velocity_buffer
        )

        scale_ratio = (
            torso_length
            / baseline_length
        )

        standing_like = (
            smooth_knee
            >= self.standing_like_angle
        )

        rep_completed = False
        rep_summary = None
        rep_aborted = False
        baseline_reset = False

        vertical_shift = max(
            abs(
                shoulder_descent
            ),
            abs(
                hip_descent
            )
        )

        baseline_mismatch = (
            standing_like
            and (
                vertical_shift
                > self.reanchor_vertical_shift
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
                shoulder,
                hip
            )

            self.knee_buffer.append(
                knee_angle
            )
            self.hip_buffer.append(
                hip_angle
            )
            self.trunk_buffer.append(
                trunk_lean
            )
            self.head_buffer.append(
                head_forward
            )
            self.shin_buffer.append(
                shin_angle
            )
            self.sync_buffer.append(
                0.0
            )

            smooth_knee = knee_angle
            smooth_hip = hip_angle
            smooth_trunk = trunk_lean
            smooth_head = head_forward
            smooth_shin_angle = shin_angle
            smooth_sync = 0.0
            smooth_knee_velocity = 0.0
            shoulder_descent = 0.0
            hip_descent = 0.0
            scale_ratio = 1.0

        if not baseline_reset:
            if self.phase == "STANDING":
                self.update_baseline(
                    shoulder,
                    hip
                )

                if (
                    smooth_knee
                    < self.start_angle
                    and smooth_knee_velocity
                    < -0.15
                ):
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
                    self.current_min_knee_angle = (
                        smooth_knee
                    )
                    self.current_min_hip_angle = (
                        smooth_hip
                    )

            elif self.phase == "DESCENDING":
                returned_to_standing = (
                    standing_like
                    and smooth_knee_velocity
                    >= -0.10
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
                        shoulder,
                        hip
                    )

                    self.knee_buffer.append(
                        knee_angle
                    )
                    self.hip_buffer.append(
                        hip_angle
                    )
                    self.trunk_buffer.append(
                        trunk_lean
                    )
                    self.head_buffer.append(
                        head_forward
                    )
                    self.shin_buffer.append(
                        shin_angle
                    )
                    self.sync_buffer.append(
                        0.0
                    )

                    smooth_knee = knee_angle
                    smooth_hip = hip_angle
                    smooth_trunk = trunk_lean
                    smooth_head = head_forward
                    smooth_shin_angle = shin_angle
                    smooth_sync = 0.0
                    smooth_knee_velocity = 0.0
                    shoulder_descent = 0.0
                    hip_descent = 0.0
                    scale_ratio = 1.0

                else:
                    bottom_signal = (
                        smooth_knee
                        < self.bottom_angle
                        and (
                            abs(
                                smooth_knee_velocity
                            )
                            < 0.30
                            or smooth_knee_velocity
                            > 0.10
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
                if smooth_knee_velocity > 0.15:
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
                        shoulder_descent
                    )
                    self.ascent_start_hip_descent = (
                        hip_descent
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
                        - shoulder_descent
                    ) / shoulder_range

                    hip_progress = (
                        self.ascent_start_hip_descent
                        - hip_descent
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
                    smooth_knee
                    > self.standing_angle
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
            if (
                smooth_knee
                < self.current_min_knee_angle
            ):
                self.current_min_knee_angle = (
                    smooth_knee
                )
                self.current_shin_angle_at_min_knee = (
                    smooth_shin_angle
                )

            self.current_max_knee_angle = max(
                self.current_max_knee_angle,
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
            self.current_max_depth_margin = max(
                self.current_max_depth_margin,
                depth_margin
            )

            current_ascent_sync = (
                median(
                    self.ascent_sync_buffer
                )
                if self.ascent_sync_buffer
                else None
            )

            self._record_phase_metrics(
                self.phase,
                smooth_knee,
                smooth_hip,
                smooth_trunk,
                smooth_shin_angle,
                smooth_head,
                smooth_sync,
                current_ascent_sync,
                depth_margin
            )

        current_depth_margin = max(
            self.current_max_depth_margin,
            depth_margin
        )

        general_depth_min = VISION_TOLERANCE[
            "general_depth_margin_min"
        ]
        ipf_depth_min = VISION_TOLERANCE[
            "ipf_depth_margin_min"
        ]

        if self.phase == "STANDING":
            depth = "READY"
        elif current_depth_margin >= ipf_depth_min:
            depth = "BELOW PARALLEL"
        elif current_depth_margin >= general_depth_min:
            depth = "PARALLEL"
        else:
            depth = "ABOVE PARALLEL"

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
            "knee_angle": smooth_knee,
            "hip_angle": smooth_hip,
            "shin_angle": smooth_shin_angle,
            "trunk_lean": smooth_trunk,
            "head_forward": smooth_head,
            "shoulder_hip_sync": smooth_sync,
            "ascent_sync_error": (
                median(
                    self.ascent_sync_buffer
                )
                if self.ascent_sync_buffer
                else None
            ),
            "knee_velocity": smooth_knee_velocity,
            "shoulder_descent": shoulder_descent,
            "hip_descent": hip_descent,
            "body_scale_ratio": scale_ratio,
            "depth_margin": depth_margin,
            "depth_standard_met": (
                current_depth_margin
                >= general_depth_min
            ),
            "ipf_depth_proxy_met": (
                current_depth_margin
                >= ipf_depth_min
            ),
            "rom_degrees": max(
                0.0,
                180.0
                - self.current_min_knee_angle
            ),
            "phase_elapsed": phase_elapsed,
            "depth": depth,
            "last_rep": self.last_rep
        }

    def reset(self):
        self.phase = "STANDING"

        self.reset_phase_counters()
        self.clear_motion_buffers()

        self.baseline_shoulder_y = None
        self.baseline_hip_y = None
        self.baseline_torso_length = None

        self.reset_rep_metrics()
