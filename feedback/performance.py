from statistics import mean


class SessionPerformanceAnalyzer:
    """
    训练组表现分析。

    这是训练辅助指标，不是医学诊断。
    目标：
    - 统一 FRONT / SIDE 每次动作数据
    - 生成单次 Rep 质量指标
    - 生成 Set Summary
    - 观察动作质量和节奏是否随次数下降
    """

    def __init__(self):
        self.reps = []

    @staticmethod
    def _clamp(value, low=0.0, high=100.0):
        return max(low, min(high, value))

    @staticmethod
    def _safe(value, default=0.0):
        if value is None:
            return default
        return float(value)

    def analyze_rep(self, rep_data):
        view = rep_data.get("view", "UNKNOWN")

        issues = []
        component_scores = {}

        if view == "SIDE":
            min_knee = self._safe(
                rep_data.get("min_knee_angle"),
                180.0
            )
            trunk = self._safe(
                rep_data.get("max_trunk_lean"),
                0.0
            )
            head = self._safe(
                rep_data.get("max_head_forward"),
                0.0
            )
            sync = self._safe(
                rep_data.get("max_sync_error"),
                0.0
            )

            # 深度：85~120°给较高分，过浅明显扣分。
            if min_knee <= 120:
                depth_score = 100.0
            else:
                depth_score = self._clamp(
                    100.0 - (min_knee - 120.0) * 2.0
                )
                issues.append("DEPTH")

            # 根据目前侧面实测阈值：17°舒适，20°以上提示。
            if trunk <= 17.0:
                trunk_score = 100.0
            elif trunk <= 20.0:
                trunk_score = 85.0
            else:
                trunk_score = self._clamp(
                    85.0 - (trunk - 20.0) * 3.0
                )
                issues.append("TRUNK")

            if head <= 0.35:
                head_score = 100.0
            elif head <= 0.55:
                head_score = 85.0
            else:
                head_score = self._clamp(
                    85.0 - (head - 0.55) * 100.0
                )
                issues.append("HEAD")

            if sync <= 0.20:
                sync_score = 100.0
            elif sync <= 0.40:
                sync_score = 85.0
            else:
                sync_score = self._clamp(
                    85.0 - (sync - 0.40) * 80.0
                )
                issues.append("SYNC")

            component_scores = {
                "depth": round(depth_score, 1),
                "trunk": round(trunk_score, 1),
                "head": round(head_score, 1),
                "sync": round(sync_score, 1)
            }

        elif view == "FRONT":
            head = self._safe(
                rep_data.get("max_head_shift"),
                0.0
            )
            shoulder = self._safe(
                rep_data.get("max_shoulder_tilt"),
                0.0
            )
            center = self._safe(
                rep_data.get("max_center_shift"),
                0.0
            )
            sync = self._safe(
                rep_data.get("max_sync_error"),
                0.0
            )

            if head <= 0.15:
                head_score = 100.0
            elif head <= 0.30:
                head_score = 85.0
            else:
                head_score = self._clamp(
                    85.0 - (head - 0.30) * 100.0
                )
                issues.append("HEAD")

            if shoulder <= 0.08:
                shoulder_score = 100.0
            elif shoulder <= 0.16:
                shoulder_score = 85.0
            else:
                shoulder_score = self._clamp(
                    85.0 - (shoulder - 0.16) * 120.0
                )
                issues.append("SHOULDER")

            if center <= 0.15:
                center_score = 100.0
            elif center <= 0.30:
                center_score = 85.0
            else:
                center_score = self._clamp(
                    85.0 - (center - 0.30) * 100.0
                )
                issues.append("CENTER")

            if sync <= 0.08:
                sync_score = 100.0
            elif sync <= 0.18:
                sync_score = 85.0
            else:
                sync_score = self._clamp(
                    85.0 - (sync - 0.18) * 120.0
                )
                issues.append("SYNC")

            component_scores = {
                "head": round(head_score, 1),
                "shoulder": round(shoulder_score, 1),
                "center": round(center_score, 1),
                "sync": round(sync_score, 1)
            }

        else:
            component_scores = {
                "general": 0.0
            }

        quality_score = mean(
            component_scores.values()
        )

        total_time = self._safe(
            rep_data.get("total_time"),
            0.0
        )

        analyzed = {
            **rep_data,
            "quality_score": round(
                quality_score,
                1
            ),
            "quality_label": self.get_quality_label(
                quality_score
            ),
            "component_scores": component_scores,
            "issues": issues,
            "tempo_total": total_time
        }

        self.reps.append(
            analyzed
        )

        return analyzed

    @staticmethod
    def get_quality_label(score):
        if score >= 90:
            return "STABLE"
        if score >= 75:
            return "GOOD"
        if score >= 60:
            return "WATCH"
        return "CHECK FORM"

    def get_set_summary(self):
        if not self.reps:
            return {
                "reps": 0,
                "average_score": 0.0,
                "best_rep": None,
                "tempo_change": 0.0,
                "quality_change": 0.0,
                "trend": "NO DATA"
            }

        scores = [
            rep["quality_score"]
            for rep in self.reps
        ]

        valid_tempos = [
            rep["tempo_total"]
            for rep in self.reps
            if rep.get("tempo_total", 0.0) > 0
        ]

        average_score = mean(
            scores
        )

        best_index = max(
            range(len(scores)),
            key=scores.__getitem__
        )

        quality_change = 0.0
        tempo_change = 0.0

        if len(scores) >= 4:
            window = min(
                3,
                len(scores) // 2
            )

            early_score = mean(
                scores[:window]
            )
            late_score = mean(
                scores[-window:]
            )

            quality_change = (
                late_score - early_score
            )

        if len(valid_tempos) >= 4:
            window = min(
                3,
                len(valid_tempos) // 2
            )

            early_tempo = mean(
                valid_tempos[:window]
            )
            late_tempo = mean(
                valid_tempos[-window:]
            )

            if early_tempo > 0:
                tempo_change = (
                    (
                        late_tempo
                        - early_tempo
                    )
                    / early_tempo
                    * 100.0
                )

        # 只描述动作表现趋势，不把它当成医学疲劳诊断。
        if len(scores) < 4:
            trend = "COLLECTING"
        elif quality_change <= -10:
            trend = "QUALITY DROPPING"
        elif tempo_change >= 20:
            trend = "SLOWING DOWN"
        else:
            trend = "STABLE"

        return {
            "reps": len(self.reps),
            "average_score": round(
                average_score,
                1
            ),
            "best_rep": self.reps[
                best_index
            ].get(
                "rep"
            ),
            "tempo_change": round(
                tempo_change,
                1
            ),
            "quality_change": round(
                quality_change,
                1
            ),
            "trend": trend
        }

    def reset(self):
        self.reps.clear()
