from pose.angles import calculate_angle


class SquatCounter:
    def __init__(self):
        self.count = 0
        self.stage = "unknown"

        # 计数阈值
        self.down_threshold = 120
        self.up_threshold = 155

        # 连续帧确认
        self.up_frames = 0
        self.down_frames = 0

        self.min_up_frames = 8
        self.min_down_frames = 8

        self.ready = False

    def calculate_angle(self, hip, knee, ankle):
        return calculate_angle(
            hip,
            knee,
            ankle
        )

    def update_with_angle(self, angle):

        rep_completed = False

        # =====================================
        # 站立区域
        # =====================================

        if angle > self.up_threshold:

            self.up_frames += 1
            self.down_frames = 0

            if self.up_frames >= self.min_up_frames:

                # 之前已经稳定蹲下
                # 现在重新站起
                if (
                    self.stage == "down"
                    and
                    self.ready
                ):
                    self.count += 1

                    rep_completed = True

                    self.ready = False

                self.stage = "up"

        # =====================================
        # 下蹲区域
        # =====================================

        elif angle < self.down_threshold:

            self.down_frames += 1
            self.up_frames = 0

            if self.down_frames >= self.min_down_frames:

                if self.stage == "up":

                    self.stage = "down"

                    self.ready = True

        # =====================================
        # 中间区域
        # =====================================

        else:

            self.up_frames = 0
            self.down_frames = 0

        return (
            self.count,
            self.stage,
            rep_completed
        )

    def reset_tracking_state(self):

        # 不清零总次数
        self.stage = "unknown"

        self.up_frames = 0
        self.down_frames = 0

        self.ready = False