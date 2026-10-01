from collections import Counter
from statistics import mean, pstdev


class SessionPerformanceAnalyzer:
    """
    训练组表现分析。

    这是训练辅助指标，不是医学诊断。
    目标：
    - 统一 FRONT / SIDE 每次动作数据
    - 生成单次 Rep 质量指标
    - 标记明显的跟踪/状态机异常 Rep
    - 生成 Set Summary
    - 观察动作质量、节奏与 ROM 一致性
    """

    def __init__(self):
        self.reps = []

    @staticmethod
    def _clamp(value, low=0.0, high=100.0):
        return max(
            low,
            min(
                high,
                value
            )
        )

    @staticmethod
    def _safe(value, default=0.0):
        if value is None:
            return default
        return float(value)

    @staticmethod
    def _coefficient_of_variation(
        values
    ):
        cleaned = [
            float(value)
            for value in values
            if (
                value is not None
                and float(value) > 0
            )
        ]

        if len(cleaned) < 3:
            return None

        average = mean(
            cleaned
        )

        if average <= 0:
            return None

        return (
            pstdev(
                cleaned
            )
            / average
            * 100.0
        )

    @staticmethod
    def _consistency_label(
        values
    ):
        available = [
            value
            for value in values
            if value is not None
        ]

        if not available:
            return "COLLECTING"

        worst_cv = max(
            available
        )

        if worst_cv <= 10.0:
            return "CONSISTENT"

        if worst_cv <= 20.0:
            return "MODERATE"

        return "VARIABLE"

    def assess_rep_confidence(
        self,
        rep_data
    ):
        """
        区分动作质量问题与明显的数据异常。

        只过滤极端异常，不把一般的坏动作当作无效数据。
        """
        reasons = []

        view = rep_data.get(
            "view",
            "UNKNOWN"
        )

        total_time = self._safe(
            rep_data.get(
                "total_time"
            ),
            0.0
        )

        if (
            total_time <= 0.35
            or total_time > 12.0
        ):
            reasons.append(
                "TEMPO_OUTLIER"
            )

        for key in (
            "descent_time",
            "bottom_time",
            "ascent_time"
        ):
            value = rep_data.get(
                key
            )

            if value is None:
                continue

            value = self._safe(
                value,
                0.0
            )

            if (
                value < 0
                or value > 8.0
            ):
                if (
                    "TEMPO_OUTLIER"
                    not in reasons
                ):
                    reasons.append(
                        "TEMPO_OUTLIER"
                    )

        if view == "FRONT":
            left_inward = self._safe(
                rep_data.get(
                    "max_left_inward"
                ),
                0.0
            )
            right_inward = self._safe(
                rep_data.get(
                    "max_right_inward"
                ),
                0.0
            )
            center = self._safe(
                rep_data.get(
                    "max_center_shift"
                ),
                0.0
            )
            sync = self._safe(
                rep_data.get(
                    "max_sync_error"
                ),
                0.0
            )

            if (
                max(
                    left_inward,
                    right_inward
                ) > 1.0
                or center > 1.25
                or sync > 0.80
            ):
                reasons.append(
                    "TRACKING_OUTLIER"
                )

        elif view == "SIDE":
            trunk = self._safe(
                rep_data.get(
                    "max_trunk_lean"
                ),
                0.0
            )
            head = self._safe(
                rep_data.get(
                    "max_head_forward"
                ),
                0.0
            )
            sync = self._safe(
                rep_data.get(
                    "max_sync_error"
                ),
                0.0
            )

            if (
                trunk > 80.0
                or head > 2.0
                or sync > 1.5
            ):
                reasons.append(
                    "TRACKING_OUTLIER"
                )

        return (
            len(
                reasons
            ) == 0,
            reasons
        )

    @staticmethod
    def _median(
        values
    ):
        cleaned = sorted(
            float(value)
            for value in values
            if value is not None
        )

        if not cleaned:
            return None

        middle = len(
            cleaned
        ) // 2

        if len(
            cleaned
        ) % 2:
            return cleaned[
                middle
            ]

        return (
            cleaned[
                middle - 1
            ]
            + cleaned[
                middle
            ]
        ) / 2

    def _apply_relative_set_filter(
        self,
        reps
    ):
        """
        在同一组内识别明显的相对异常 Rep。

        只在同一视角至少有 4 次时启用，避免样本太少时过拟合。
        """
        for rep in reps:
            rep[
                "set_valid"
            ] = True
            rep[
                "set_exclusion_reasons"
            ] = []

        for view in (
            "FRONT",
            "SIDE"
        ):
            view_reps = [
                rep
                for rep in reps
                if (
                    rep.get(
                        "view"
                    ) == view
                    and rep.get(
                        "analysis_valid",
                        True
                    )
                )
            ]

            if len(
                view_reps
            ) < 4:
                continue

            tempo_median = self._median([
                rep.get(
                    "total_time"
                )
                for rep in view_reps
            ])

            rom_key = (
                "rom"
                if view == "FRONT"
                else "rom_degrees"
            )

            rom_median = self._median([
                rep.get(
                    rom_key
                )
                for rep in view_reps
            ])

            for rep in view_reps:
                reasons = []

                total_time = rep.get(
                    "total_time"
                )

                if (
                    tempo_median
                    and total_time
                ):
                    tempo_ratio = (
                        float(
                            total_time
                        )
                        / tempo_median
                    )

                    if (
                        tempo_ratio < 0.45
                        or tempo_ratio > 2.20
                    ):
                        reasons.append(
                            "SET_TEMPO_OUTLIER"
                        )

                rom_value = rep.get(
                    rom_key
                )

                if (
                    rom_median
                    and rom_value
                ):
                    rom_ratio = (
                        float(
                            rom_value
                        )
                        / rom_median
                    )

                    if (
                        rom_ratio < 0.55
                        or rom_ratio > 1.80
                    ):
                        reasons.append(
                            "SET_ROM_OUTLIER"
                        )

                if reasons:
                    rep[
                        "set_valid"
                    ] = False
                    rep[
                        "set_exclusion_reasons"
                    ] = reasons

        return [
            rep
            for rep in reps
            if (
                rep.get(
                    "analysis_valid",
                    True
                )
                and rep.get(
                    "set_valid",
                    True
                )
            )
        ]

    def score_front_knee_tracking(
        self,
        rep_data,
        issues
    ):
        left_inward = self._safe(
            rep_data.get(
                "max_left_inward",
                rep_data.get(
                    "left_inward",
                    0.0
                )
            ),
            0.0
        )

        right_inward = self._safe(
            rep_data.get(
                "max_right_inward",
                rep_data.get(
                    "right_inward",
                    0.0
                )
            ),
            0.0
        )

        max_inward = max(
            0.0,
            left_inward,
            right_inward
        )

        # 当前测试阈值来自实际摄像头校准：
        # <0.05 稳定，>0.15 明显内扣。
        if max_inward <= 0.05:
            score = 100.0
        elif max_inward <= 0.15:
            progress = (
                max_inward - 0.05
            ) / 0.10

            score = (
                100.0
                - 15.0 * progress
            )
        else:
            score = self._clamp(
                85.0
                - (
                    max_inward - 0.15
                ) * 140.0
            )
            issues.append(
                "KNEE_TRACKING"
            )

        return score

    def score_front_symmetry(
        self,
        rep_data,
        issues
    ):
        symmetry = self._safe(
            rep_data.get(
                "max_symmetry_value",
                rep_data.get(
                    "symmetry_value",
                    0.0
                )
            ),
            0.0
        )

        # 正常不对称约 0.25，明显偏侧约 1.09。
        if symmetry <= 0.35:
            score = 100.0
        elif symmetry <= 0.60:
            progress = (
                symmetry - 0.35
            ) / 0.25

            score = (
                100.0
                - 15.0 * progress
            )
        else:
            score = self._clamp(
                85.0
                - (
                    symmetry - 0.60
                ) * 60.0
            )
            issues.append(
                "ASYMMETRY"
            )

        return score

    def analyze_rep(self, rep_data):
        view = rep_data.get(
            "view",
            "UNKNOWN"
        )

        issues = []
        component_scores = {}

        if view == "SIDE":
            min_knee = self._safe(
                rep_data.get(
                    "min_knee_angle"
                ),
                180.0
            )
            trunk = self._safe(
                rep_data.get(
                    "max_trunk_lean"
                ),
                0.0
            )
            head = self._safe(
                rep_data.get(
                    "max_head_forward"
                ),
                0.0
            )
            sync = self._safe(
                rep_data.get(
                    "max_sync_error"
                ),
                0.0
            )

            if min_knee <= 120:
                depth_score = 100.0
            else:
                depth_score = self._clamp(
                    100.0
                    - (
                        min_knee
                        - 120.0
                    ) * 2.0
                )
                issues.append(
                    "DEPTH"
                )

            rom_degrees = max(
                0.0,
                180.0
                - min_knee
            )

            trunk_rom_ratio = (
                trunk
                / max(
                    rom_degrees,
                    1.0
                )
            )

            # 躯干前倾需要结合下蹲深度判断。
            # 深蹲越深，自然前倾通常也会增加，不能使用固定 17/20 度
            # 对所有深度一刀切。
            if trunk_rom_ratio <= 0.40:
                trunk_score = 100.0
            elif trunk_rom_ratio <= 0.55:
                progress = (
                    trunk_rom_ratio
                    - 0.40
                ) / 0.15

                trunk_score = (
                    100.0
                    - 15.0 * progress
                )
            else:
                trunk_score = self._clamp(
                    85.0
                    - (
                        trunk_rom_ratio
                        - 0.55
                    ) * 100.0
                )

                issues.append(
                    "TRUNK"
                )

            if head <= 0.35:
                head_score = 100.0
            elif head <= 0.55:
                head_score = 85.0
            else:
                head_score = self._clamp(
                    85.0
                    - (
                        head
                        - 0.55
                    ) * 100.0
                )
                issues.append(
                    "HEAD"
                )

            if sync <= 0.20:
                sync_score = 100.0
            elif sync <= 0.40:
                sync_score = 85.0
            else:
                sync_score = self._clamp(
                    85.0
                    - (
                        sync
                        - 0.40
                    ) * 80.0
                )
                issues.append(
                    "SYNC"
                )

            component_scores = {
                "depth": round(
                    depth_score,
                    1
                ),
                "trunk": round(
                    trunk_score,
                    1
                ),
                "head": round(
                    head_score,
                    1
                ),
                "sync": round(
                    sync_score,
                    1
                )
            }

        elif view == "FRONT":
            head = self._safe(
                rep_data.get(
                    "max_head_shift"
                ),
                0.0
            )
            shoulder = self._safe(
                rep_data.get(
                    "max_shoulder_tilt"
                ),
                0.0
            )
            center = self._safe(
                rep_data.get(
                    "max_center_shift"
                ),
                0.0
            )
            sync = self._safe(
                rep_data.get(
                    "max_sync_error"
                ),
                0.0
            )

            if head <= 0.15:
                head_score = 100.0
            elif head <= 0.30:
                head_score = 85.0
            else:
                head_score = self._clamp(
                    85.0
                    - (
                        head
                        - 0.30
                    ) * 100.0
                )
                issues.append(
                    "HEAD"
                )

            if shoulder <= 0.08:
                shoulder_score = 100.0
            elif shoulder <= 0.16:
                shoulder_score = 85.0
            else:
                shoulder_score = self._clamp(
                    85.0
                    - (
                        shoulder
                        - 0.16
                    ) * 120.0
                )
                issues.append(
                    "SHOULDER"
                )

            if center <= 0.15:
                center_score = 100.0
            elif center <= 0.30:
                center_score = 85.0
            else:
                center_score = self._clamp(
                    85.0
                    - (
                        center
                        - 0.30
                    ) * 100.0
                )
                issues.append(
                    "CENTER"
                )

            if sync <= 0.08:
                sync_score = 100.0
            elif sync <= 0.18:
                sync_score = 85.0
            else:
                sync_score = self._clamp(
                    85.0
                    - (
                        sync
                        - 0.18
                    ) * 120.0
                )
                issues.append(
                    "SYNC"
                )

            knee_tracking_score = (
                self.score_front_knee_tracking(
                    rep_data,
                    issues
                )
            )

            symmetry_score = (
                self.score_front_symmetry(
                    rep_data,
                    issues
                )
            )

            component_scores = {
                "head": round(
                    head_score,
                    1
                ),
                "shoulder": round(
                    shoulder_score,
                    1
                ),
                "center": round(
                    center_score,
                    1
                ),
                "sync": round(
                    sync_score,
                    1
                ),
                "knee_tracking": round(
                    knee_tracking_score,
                    1
                ),
                "symmetry": round(
                    symmetry_score,
                    1
                )
            }

        else:
            component_scores = {
                "general": 0.0
            }

        quality_score = mean(
            component_scores.values()
        )

        total_time = self._safe(
            rep_data.get(
                "total_time"
            ),
            0.0
        )

        (
            analysis_valid,
            confidence_reasons
        ) = self.assess_rep_confidence(
            rep_data
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
            "tempo_total": total_time,
            "trunk_rom_ratio": (
                round(
                    trunk_rom_ratio,
                    3
                )
                if view == "SIDE"
                else None
            ),
            "analysis_valid": analysis_valid,
            "confidence_reasons": confidence_reasons
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
                "valid_reps": 0,
                "excluded_reps": 0,
                "average_score": 0.0,
                "best_rep": None,
                "tempo_change": 0.0,
                "quality_change": 0.0,
                "tempo_cv": None,
                "front_rom_cv": None,
                "side_rom_cv": None,
                "consistency_label": "NO DATA",
                "trend": "NO DATA",
                "top_issue": "NONE"
            }

        valid_reps = self._apply_relative_set_filter(
            self.reps
        )

        if not valid_reps:
            return {
                "reps": len(
                    self.reps
                ),
                "valid_reps": 0,
                "excluded_reps": len(
                    self.reps
                ),
                "average_score": 0.0,
                "best_rep": None,
                "tempo_change": 0.0,
                "quality_change": 0.0,
                "tempo_cv": None,
                "front_rom_cv": None,
                "side_rom_cv": None,
                "consistency_label": "NO VALID DATA",
                "trend": "NO VALID DATA",
                "top_issue": "NONE"
            }

        scores = [
            rep["quality_score"]
            for rep in valid_reps
        ]

        valid_tempos = [
            rep["tempo_total"]
            for rep in valid_reps
            if rep.get(
                "tempo_total",
                0.0
            ) > 0
        ]

        front_roms = [
            rep.get(
                "rom"
            )
            for rep in valid_reps
            if (
                rep.get(
                    "view"
                ) == "FRONT"
                and rep.get(
                    "rom"
                ) is not None
                and rep.get(
                    "rom"
                ) > 0
            )
        ]

        side_roms = [
            rep.get(
                "rom_degrees"
            )
            for rep in valid_reps
            if (
                rep.get(
                    "view"
                ) == "SIDE"
                and rep.get(
                    "rom_degrees"
                ) is not None
                and rep.get(
                    "rom_degrees"
                ) > 0
            )
        ]

        average_score = mean(
            scores
        )

        best_rep = max(
            valid_reps,
            key=lambda rep: rep[
                "quality_score"
            ]
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
                late_score
                - early_score
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

        tempo_cv = self._coefficient_of_variation(
            valid_tempos
        )
        front_rom_cv = self._coefficient_of_variation(
            front_roms
        )
        side_rom_cv = self._coefficient_of_variation(
            side_roms
        )

        consistency_label = self._consistency_label([
            tempo_cv,
            front_rom_cv,
            side_rom_cv
        ])

        if len(scores) < 4:
            trend = "COLLECTING"
        elif quality_change <= -10:
            trend = "QUALITY DROPPING"
        elif tempo_change >= 20:
            trend = "SLOWING DOWN"
        else:
            trend = "STABLE"

        issue_counter = Counter()

        for rep in valid_reps:
            issue_counter.update(
                rep.get(
                    "issues",
                    []
                )
            )

        if issue_counter:
            top_issue = issue_counter.most_common(
                1
            )[0][0]
        else:
            top_issue = "NONE"

        return {
            "reps": len(
                self.reps
            ),
            "valid_reps": len(
                valid_reps
            ),
            "excluded_reps": (
                len(
                    self.reps
                )
                - len(
                    valid_reps
                )
            ),
            "relative_excluded_reps": sum(
                1
                for rep in self.reps
                if (
                    rep.get(
                        "analysis_valid",
                        True
                    )
                    and not rep.get(
                        "set_valid",
                        True
                    )
                )
            ),
            "average_score": round(
                average_score,
                1
            ),
            "best_rep": best_rep.get(
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
            "tempo_cv": (
                round(
                    tempo_cv,
                    1
                )
                if tempo_cv is not None
                else None
            ),
            "front_rom_cv": (
                round(
                    front_rom_cv,
                    1
                )
                if front_rom_cv is not None
                else None
            ),
            "side_rom_cv": (
                round(
                    side_rom_cv,
                    1
                )
                if side_rom_cv is not None
                else None
            ),
            "consistency_label": consistency_label,
            "trend": trend,
            "top_issue": top_issue
        }

    def reset(self):
        self.reps.clear()
