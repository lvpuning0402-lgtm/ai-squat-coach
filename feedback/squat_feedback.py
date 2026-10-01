import math
from collections import deque


class SquatFeedback:
    def __init__(self):

        # =====================================
        # 当前一次深蹲
        # =====================================

        self.current_min_knee_angle = 180.0

        self.current_trunk_angles = []

        # =====================================
        # 实时状态
        # =====================================

        self.depth_state = "READY"

        self.trunk_state = "READY"

        # =====================================
        # 躯干状态稳定
        # =====================================

        self.bad_trunk_frames = 0

        self.good_trunk_frames = 0

        self.required_trunk_frames = 8

        # =====================================
        # 经过你实际测试后的阈值
        #
        # 右侧正常深蹲：
        # 约 12~14°
        #
        # 故意明显前倾：
        # 约 25°
        # =====================================

        self.trunk_bad_threshold = 20.0

        self.trunk_good_threshold = 17.0

        # =====================================
        # 完成动作提示
        # =====================================

        self.good_rep_frames = 0

        # =====================================
        # 历史
        # =====================================

        self.rep_history = []

        # =====================================
        # 躯干平滑
        # =====================================

        self.trunk_smooth_buffer = deque(
            maxlen=15
        )

    def calculate_trunk_inclination(
        self,
        shoulder,
        hip
    ):
        dx = (
            shoulder[0]
            -
            hip[0]
        )

        dy = (
            shoulder[1]
            -
            hip[1]
        )

        angle = math.degrees(
            math.atan2(
                abs(dx),
                abs(dy)
            )
        )

        return angle

    def smooth_trunk_angle(
        self,
        raw_angle
    ):
        self.trunk_smooth_buffer.append(
            raw_angle
        )

        values = sorted(
            self.trunk_smooth_buffer
        )

        if not values:
            return raw_angle

        if len(values) >= 5:
            values = values[1:-1]

        return (
            sum(values)
            /
            len(values)
        )

    def update_current_rep(
        self,
        knee_angle,
        trunk_angle,
        stage,
        trunk_valid
    ):
        if stage != "down":
            return

        # =====================================
        # 深度始终可以记录
        # =====================================

        if (
            knee_angle
            <
            self.current_min_knee_angle
        ):
            self.current_min_knee_angle = (
                knee_angle
            )

        # =====================================
        # 只有侧面视角
        # 才记录躯干角
        # =====================================

        if trunk_valid:

            if (
                0
                <=
                trunk_angle
                <=
                60
            ):
                self.current_trunk_angles.append(
                    trunk_angle
                )

    def get_depth_feedback(
        self,
        knee_angle,
        stage
    ):
        if self.good_rep_frames > 0:

            self.good_rep_frames -= 1

            return "REP COMPLETE"

        if stage == "up":

            self.depth_state = "READY"

            return "READY"

        if stage == "down":

            depth_angle = (
                self.current_min_knee_angle
            )

            if depth_angle < 85:

                self.depth_state = (
                    "VERY DEEP"
                )

            elif depth_angle <= 120:

                if (
                    self.depth_state
                    !=
                    "VERY DEEP"
                ):
                    self.depth_state = (
                        "GOOD DEPTH"
                    )

            else:

                if self.depth_state not in (
                    "GOOD DEPTH",
                    "VERY DEEP"
                ):
                    self.depth_state = (
                        "GO DEEPER"
                    )

            return self.depth_state

        return "READY"

    def get_trunk_feedback(
        self,
        trunk_angle,
        stage,
        trunk_valid
    ):
        # =====================================
        # 不是侧面
        # 不评价躯干
        # =====================================

        if not trunk_valid:

            self.trunk_state = (
                "TURN SIDEWAYS"
            )

            self.bad_trunk_frames = 0
            self.good_trunk_frames = 0

            return self.trunk_state

        # =====================================
        # 侧面站立准备
        # =====================================

        if stage == "up":

            self.trunk_state = "READY"

            self.bad_trunk_frames = 0
            self.good_trunk_frames = 0

            return self.trunk_state

        # =====================================
        # 前倾过多
        # =====================================

        if (
            trunk_angle
            >
            self.trunk_bad_threshold
        ):

            self.bad_trunk_frames += 1

            self.good_trunk_frames = 0

            if (
                self.bad_trunk_frames
                >=
                self.required_trunk_frames
            ):
                self.trunk_state = (
                    "LEANING TOO MUCH"
                )

        # =====================================
        # 正常
        # =====================================

        elif (
            trunk_angle
            <
            self.trunk_good_threshold
        ):

            self.good_trunk_frames += 1

            self.bad_trunk_frames = 0

            if (
                self.good_trunk_frames
                >=
                self.required_trunk_frames
            ):
                self.trunk_state = (
                    "TRUNK OK"
                )

        # 17~20°缓冲区
        else:

            self.bad_trunk_frames = 0
            self.good_trunk_frames = 0

        return self.trunk_state

    def calculate_rep_trunk_value(
        self
    ):
        if not self.current_trunk_angles:
            return None

        values = sorted(
            self.current_trunk_angles
        )

        index = int(
            len(values)
            *
            0.90
        )

        if index >= len(values):

            index = (
                len(values)
                -
                1
            )

        return values[index]

    def complete_rep(
        self,
        rep_number
    ):
        min_knee = (
            self.current_min_knee_angle
        )

        stable_trunk = (
            self.calculate_rep_trunk_value()
        )

        # =====================================
        # 深度
        # =====================================

        depth_ok = (
            min_knee
            <=
            120
        )

        # =====================================
        # 躯干
        # =====================================

        trunk_analyzed = (
            stable_trunk
            is not None
        )

        if trunk_analyzed:

            trunk_ok = (
                stable_trunk
                <=
                self.trunk_bad_threshold
            )

        else:

            trunk_ok = None

        # =====================================
        # 错误列表
        # =====================================

        issues = []

        if not depth_ok:

            issues.append(
                "NOT DEEP ENOUGH"
            )

        if trunk_analyzed:

            if not trunk_ok:

                issues.append(
                    "TOO MUCH FORWARD LEAN"
                )

        else:

            issues.append(
                "TURN SIDEWAYS FOR TRUNK CHECK"
            )

        # =====================================
        # 最终结果
        # =====================================

        if (
            depth_ok
            and
            trunk_analyzed
            and
            trunk_ok
        ):
            result = "GOOD"

        elif (
            not depth_ok
            or
            (
                trunk_analyzed
                and
                not trunk_ok
            )
        ):
            result = "CHECK FORM"

        else:
            result = "VIEW NEEDED"

        rep_data = {
            "rep":
                rep_number,

            "min_knee_angle":
                min_knee,

            "stable_trunk_lean":
                stable_trunk,

            "trunk_analyzed":
                trunk_analyzed,

            "depth_ok":
                depth_ok,

            "trunk_ok":
                trunk_ok,

            "result":
                result,

            "issues":
                issues
        }

        self.rep_history.append(
            rep_data
        )

        self.good_rep_frames = 30

        self.reset_current_rep()

        return rep_data

    def get_session_stats(
        self
    ):
        total = len(
            self.rep_history
        )

        analyzed = sum(
            1
            for rep in self.rep_history
            if rep[
                "trunk_analyzed"
            ]
        )

        good = sum(
            1
            for rep in self.rep_history
            if rep["result"] == "GOOD"
        )

        if analyzed > 0:

            good_rate = (
                good
                /
                analyzed
            ) * 100

        else:

            good_rate = 0.0

        return {
            "total": total,
            "analyzed": analyzed,
            "good": good,
            "good_rate": good_rate
        }

    def reset_current_rep(
        self
    ):
        self.current_min_knee_angle = 180.0

        self.current_trunk_angles = []

        self.depth_state = "READY"

        self.trunk_state = "READY"

        self.bad_trunk_frames = 0

        self.good_trunk_frames = 0

        self.trunk_smooth_buffer.clear()