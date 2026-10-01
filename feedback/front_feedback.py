from collections import deque


class FrontFeedback:
    def __init__(self):
        self.left_valgus_buffer = deque(maxlen=10)
        self.right_valgus_buffer = deque(maxlen=10)
        self.symmetry_buffer = deque(maxlen=10)

        # 根据实际摄像头测试校准：
        # 正常深蹲约 -0.33 / -0.52
        # 故意内扣约 +0.25 / +0.19
        self.valgus_bad_threshold = 0.15
        self.valgus_good_threshold = 0.05

        # 正常不对称约 0.25，故意偏侧约 1.09
        self.symmetry_good_threshold = 0.35
        self.symmetry_bad_threshold = 0.60

        self.required_frames = 7

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
        self.last_rep_metrics = None

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

    def finalize_rep_metrics(self):
        self.last_rep_metrics = {
            "max_left_inward": self.current_max_left_inward,
            "max_right_inward": self.current_max_right_inward,
            "max_symmetry_value": self.current_max_symmetry
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
