from collections import deque

from standards.squat_standard import VISION_TOLERANCE


class FrontFeedback:
    def __init__(self):
        self.left_valgus_buffer = deque(maxlen=10)
        self.right_valgus_buffer = deque(maxlen=10)
        self.symmetry_buffer = deque(maxlen=10)

        # 动作标准：膝盖应跟随足部方向（NSCA）。
        # 下列数值是 2D 摄像头工程容差，不是个人校准值，
        # 也不是医学诊断阈值。
        self.valgus_good_threshold = VISION_TOLERANCE[
            "knee_in_good_max"
        ]
        self.valgus_bad_threshold = VISION_TOLERANCE[
            "knee_in_bad_min"
        ]

        # 左右对称性仅作为诊断指标，不作为全球动作规则。
        self.symmetry_good_threshold = VISION_TOLERANCE[
            "symmetry_good_max"
        ]
        self.symmetry_bad_threshold = VISION_TOLERANCE[
            "symmetry_bad_min"
        ]

        # UI persistence only: four consecutive frames are enough to show
        # KNEE IN. The actual standard tolerance is unchanged.
        self.required_frames = 4

        self.left_bad_frames = 0
        self.right_bad_frames = 0
        self.left_good_frames = 0
        self.right_good_frames = 0

        self.symmetry_bad_frames = 0
        self.symmetry_good_frames = 0

        self.left_knee_state = "OK"
        self.right_knee_state = "OK"
        self.symmetry_state = "OK"

        # 单次动作峰值，用于完整 Rep 质量分析。
        self.current_rep_active = False
        self.current_max_left_inward = 0.0
        self.current_max_right_inward = 0.0
        self.current_max_symmetry = 0.0
        self.phase_metrics = self._new_phase_metrics()
        self.last_rep_metrics = None

    @staticmethod
    def _new_phase_metrics():
        return {
            "descent": {
                "samples": 0,
                "max_left_inward": 0.0,
                "max_right_inward": 0.0,
                "max_symmetry_value": 0.0,
            },
            "bottom": {
                "samples": 0,
                "max_left_inward": 0.0,
                "max_right_inward": 0.0,
                "max_symmetry_value": 0.0,
            },
            "ascent": {
                "samples": 0,
                "max_left_inward": 0.0,
                "max_right_inward": 0.0,
                "max_symmetry_value": 0.0,
            },
        }

    @staticmethod
    def _phase_key(
        stage
    ):
        return {
            "DESCENDING": "descent",
            "BOTTOM": "bottom",
            "ASCENDING": "ascent",
            "down": "descent",
        }.get(
            stage
        )

    def _record_phase_metrics(
        self,
        stage,
        left_inward,
        right_inward,
        symmetry
    ):
        phase_key = self._phase_key(
            stage
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
            "max_left_inward"
        ] = max(
            metrics[
                "max_left_inward"
            ],
            left_inward
        )
        metrics[
            "max_right_inward"
        ] = max(
            metrics[
                "max_right_inward"
            ],
            right_inward
        )
        metrics[
            "max_symmetry_value"
        ] = max(
            metrics[
                "max_symmetry_value"
            ],
            symmetry
        )

    @staticmethod
    def average(buffer):
        if not buffer:
            return 0.0

        return sum(buffer) / len(buffer)

    def calculate_metrics(
        self,
        left_hip,
        right_hip,
        left_knee,
        right_knee,
        left_ankle,
        right_ankle
    ):
        mid_x = (
            left_hip[0]
            + right_hip[0]
        ) / 2

        hip_width = max(
            abs(
                right_hip[0]
                - left_hip[0]
            ),
            0.01
        )

        left_knee_mid_distance = abs(
            left_knee[0]
            - mid_x
        )
        left_ankle_mid_distance = abs(
            left_ankle[0]
            - mid_x
        )

        left_valgus = (
            left_ankle_mid_distance
            - left_knee_mid_distance
        ) / hip_width

        right_knee_mid_distance = abs(
            right_knee[0]
            - mid_x
        )
        right_ankle_mid_distance = abs(
            right_ankle[0]
            - mid_x
        )

        right_valgus = (
            right_ankle_mid_distance
            - right_knee_mid_distance
        ) / hip_width

        knee_height_difference = abs(
            left_knee[1]
            - right_knee[1]
        )

        symmetry_ratio = (
            knee_height_difference
            / hip_width
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
        if value > self.valgus_bad_threshold:
            if side == "LEFT":
                self.left_bad_frames += 1
                self.left_good_frames = 0

                if self.left_bad_frames >= self.required_frames:
                    self.left_knee_state = "KNEE IN"
            else:
                self.right_bad_frames += 1
                self.right_good_frames = 0

                if self.right_bad_frames >= self.required_frames:
                    self.right_knee_state = "KNEE IN"

        elif value < self.valgus_good_threshold:
            if side == "LEFT":
                self.left_good_frames += 1
                self.left_bad_frames = 0

                if self.left_good_frames >= self.required_frames:
                    self.left_knee_state = "OK"
            else:
                self.right_good_frames += 1
                self.right_bad_frames = 0

                if self.right_good_frames >= self.required_frames:
                    self.right_knee_state = "OK"

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
        if value > self.symmetry_bad_threshold:
            self.symmetry_bad_frames += 1
            self.symmetry_good_frames = 0

            if self.symmetry_bad_frames >= self.required_frames:
                self.symmetry_state = "ASYMMETRIC"

        elif value < self.symmetry_good_threshold:
            self.symmetry_good_frames += 1
            self.symmetry_bad_frames = 0

            if self.symmetry_good_frames >= self.required_frames:
                self.symmetry_state = "OK"

        else:
            self.symmetry_bad_frames = 0
            self.symmetry_good_frames = 0

        return self.symmetry_state

    def reset_rep_metrics(self):
        self.current_rep_active = False
        self.current_max_left_inward = 0.0
        self.current_max_right_inward = 0.0
        self.current_max_symmetry = 0.0
        self.phase_metrics = self._new_phase_metrics()

    def finalize_rep_metrics(self):
        self.last_rep_metrics = {
            "max_left_inward": self.current_max_left_inward,
            "max_right_inward": self.current_max_right_inward,
            "max_symmetry_value": self.current_max_symmetry,
            "phase_metrics": {
                phase: dict(
                    metrics
                )
                for phase, metrics
                in self.phase_metrics.items()
            }
        }

        result = dict(
            self.last_rep_metrics
        )

        self.reset_rep_metrics()

        return result

    def update(
        self,
        left_hip,
        right_hip,
        left_knee,
        right_knee,
        left_ankle,
        right_ankle,
        stage,
        rep_completed=False
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

        active_phases = {
            "DESCENDING",
            "BOTTOM",
            "ASCENDING",
            "down"
        }

        rep_metrics = None

        if stage in active_phases:
            self.current_rep_active = True

            self.current_max_left_inward = max(
                self.current_max_left_inward,
                smooth_left
            )
            self.current_max_right_inward = max(
                self.current_max_right_inward,
                smooth_right
            )
            self.current_max_symmetry = max(
                self.current_max_symmetry,
                smooth_symmetry
            )

            self._record_phase_metrics(
                stage,
                smooth_left,
                smooth_right,
                smooth_symmetry
            )

            left_state = self.update_knee_state(
                smooth_left,
                "LEFT"
            )
            right_state = self.update_knee_state(
                smooth_right,
                "RIGHT"
            )
            symmetry_state = self.update_symmetry_state(
                smooth_symmetry
            )

        else:
            left_state = "READY"
            right_state = "READY"
            symmetry_state = "READY"

            if (
                rep_completed
                and self.current_rep_active
            ):
                rep_metrics = self.finalize_rep_metrics()
            elif self.current_rep_active:
                # 动作中途取消或分析器重新建立站立基准时，
                # 不把残留峰值带到下一次 Rep。
                self.reset_rep_metrics()

        return {
            "left_state": left_state,
            "right_state": right_state,
            "symmetry_state": symmetry_state,
            "left_value": smooth_left,
            "right_value": smooth_right,
            "symmetry_value": smooth_symmetry,
            "rep_metrics": rep_metrics
        }

    def reset(self):
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

        self.last_rep_metrics = None
        self.reset_rep_metrics()
