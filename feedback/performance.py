from collections import Counter
from statistics import mean, pstdev

from standards.squat_standard import (
    STANDARD_NAME,
    VISION_TOLERANCE,
)
from feedback.competition_detail import CompetitionDetailEvaluator


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
        self.detail_evaluator = CompetitionDetailEvaluator()

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
                    "max_ascent_sync_error",
                    rep_data.get(
                        "max_sync_error"
                    )
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
                    "max_ascent_sync_error",
                    rep_data.get(
                        "max_sync_error"
                    )
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

        good_limit = VISION_TOLERANCE[
            "knee_in_good_max"
        ]
        bad_limit = VISION_TOLERANCE[
            "knee_in_bad_min"
        ]

        if max_inward <= good_limit:
            score = 100.0
        elif max_inward <= bad_limit:
            progress = (
                max_inward - good_limit
            ) / max(
                bad_limit - good_limit,
                0.001
            )

            score = (
                100.0
                - 15.0 * progress
            )
        else:
            score = self._clamp(
                85.0
                - (
                    max_inward - bad_limit
                ) * 120.0
            )
            issues.append(
                "KNEE_TRACKING"
            )

        return score

    def score_front_symmetry(
        self,
        rep_data
    ):
        """
        Symmetry is a diagnostic metric, not a universal squat pass/fail rule.
        The score is retained only for internal diagnostics and is excluded
        from the formal standard score.
        """
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

        good_limit = VISION_TOLERANCE[
            "symmetry_good_max"
        ]
        bad_limit = VISION_TOLERANCE[
            "symmetry_bad_min"
        ]

        if symmetry <= good_limit:
            return 100.0

        if symmetry <= bad_limit:
            progress = (
                symmetry - good_limit
            ) / max(
                bad_limit - good_limit,
                0.001
            )

            return (
                100.0
                - 15.0 * progress
            )

        return self._clamp(
            85.0
            - (
                symmetry - bad_limit
            ) * 80.0
        )

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
                    "max_ascent_sync_error",
                    rep_data.get(
                        "max_sync_error"
                    )
                ),
                0.0
            )

            depth_standard_met = bool(
                rep_data.get(
                    "depth_standard_met",
                    False
                )
            )

            if depth_standard_met:
                depth_score = 100.0
            else:
                depth_score = 70.0
                issues.append(
                    "DEPTH"
                )

            sync_good = VISION_TOLERANCE[
                "ascent_progress_good_max"
            ]
            sync_bad = VISION_TOLERANCE[
                "ascent_progress_bad_min"
            ]

            if sync <= sync_good:
                sync_score = 100.0
            elif sync <= sync_bad:
                progress = (
                    sync - sync_good
                ) / max(
                    sync_bad - sync_good,
                    0.001
                )
                sync_score = (
                    100.0
                    - 15.0 * progress
                )
            else:
                sync_score = self._clamp(
                    85.0
                    - (
                        sync - sync_bad
                    ) * 80.0
                )
                issues.append(
                    "SYNC"
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

            # Trunk lean and head position remain diagnostic because
            # no single universal numeric angle applies to all squat styles,
            # bar positions, anthropometry and mobility.
            diagnostic_metrics = {
                "trunk_lean": round(
                    trunk,
                    2
                ),
                "head_forward": round(
                    head,
                    3
                ),
                "trunk_rom_ratio": round(
                    trunk_rom_ratio,
                    3
                )
            }

            standard_checks = {
                "depth": depth_standard_met,
                "ascent_control": (
                    sync <= sync_bad
                )
            }
            standard_scope = "SIDE_GENERAL_STRENGTH"

            component_scores = {
                "depth": round(
                    depth_score,
                    1
                ),
                "ascent_control": round(
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
                    "max_ascent_sync_error",
                    rep_data.get(
                        "max_sync_error"
                    )
                ),
                0.0
            )

            knee_tracking_score = (
                self.score_front_knee_tracking(
                    rep_data,
                    issues
                )
            )

            symmetry_score = (
                self.score_front_symmetry(
                    rep_data
                )
            )

            sync_good = VISION_TOLERANCE[
                "ascent_progress_good_max"
            ]
            sync_bad = VISION_TOLERANCE[
                "ascent_progress_bad_min"
            ]

            if sync <= sync_good:
                sync_score = 100.0
            elif sync <= sync_bad:
                progress = (
                    sync - sync_good
                ) / max(
                    sync_bad - sync_good,
                    0.001
                )
                sync_score = (
                    100.0
                    - 15.0 * progress
                )
            else:
                sync_score = self._clamp(
                    85.0
                    - (
                        sync - sync_bad
                    ) * 80.0
                )
                issues.append(
                    "SYNC"
                )

            diagnostic_metrics = {
                "head_shift": round(
                    head,
                    3
                ),
                "shoulder_tilt": round(
                    shoulder,
                    3
                ),
                "center_shift": round(
                    center,
                    3
                ),
                "symmetry_score": round(
                    symmetry_score,
                    1
                )
            }

            standard_checks = {
                "knee_tracking": (
                    "KNEE_TRACKING"
                    not in issues
                ),
                "ascent_control": (
                    sync <= sync_bad
                )
            }
            standard_scope = "FRONT_TECHNIQUE_ONLY"

            component_scores = {
                "knee_tracking": round(
                    knee_tracking_score,
                    1
                ),
                "ascent_control": round(
                    sync_score,
                    1
                )
            }

        else:
            diagnostic_metrics = {}
            standard_checks = {}
            standard_scope = "UNKNOWN"
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

        standard_score = round(
            quality_score,
            1
        )

        standard_met = (
            all(
                standard_checks.values()
            )
            if standard_checks
            else False
        )

        detail_result = self.detail_evaluator.evaluate({
            **rep_data,
            "standard_checks": standard_checks,
            "standard_met": standard_met,
        })

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
            "standard_profile": STANDARD_NAME,
            "standard_scope": standard_scope,
            "standard_checks": standard_checks,
            "standard_score": standard_score,
            "standard_met": standard_met,
            "detail_profile": detail_result[
                "detail_profile"
            ],
            "detail_profile_version": detail_result[
                "detail_profile_version"
            ],
            "detail_score": detail_result[
                "detail_score"
            ],
            "detail_grade": detail_result.get(
                "detail_grade",
                "N/A"
            ),
            "detail_label": detail_result[
                "detail_label"
            ],
            "detail_coverage": detail_result.get(
                "detail_coverage",
                0.0
            ),
            "detail_confidence": detail_result.get(
                "detail_confidence",
                "LOW"
            ),
            "confidence_breakdown": detail_result.get("confidence_breakdown", {}),
            "detail_provisional": detail_result.get("detail_provisional", True),
            "detail_weighted_components": detail_result.get(
                "weighted_components",
                {}
            ),
            "detail_deductions": detail_result.get(
                "detail_deductions",
                []
            ),
            "phase_scores": detail_result.get(
                "phase_scores",
                {}
            ),
            "weakest_phase": detail_result.get(
                "weakest_phase"
            ),
            "detail_checks": detail_result[
                "checks"
            ],
            "detail_warnings": detail_result[
                "detail_warnings"
            ],
            "competition_flags": detail_result.get(
                "competition_flags",
                []
            ),
            "angle_metrics": detail_result[
                "angle_metrics"
            ],
            "competition_lenses": detail_result[
                "competition_lenses"
            ],
            "diagnostic_metrics": diagnostic_metrics,
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
                "average_detail_score": 0.0,
                "average_detail_coverage": 0.0,
                "average_front_physique_score": None,
                "average_side_ipf_score": None,
                "detail_component_averages": {},
                "top_detail_deductions": [],
                "phase_score_averages": {},
                "phase_coverage_averages": {},
                "phase_confidence_counts": {},
                "phase_deduction_summary": {},
                "weakest_phase": None,
                "detail_watch_reps": 0,
                "detail_watch_rate": 0.0,
                "detail_watch_events": 0,
                "detail_review_events": 0,
                "detail_clear_reps": 0,
                "top_detail_warning": "NONE",
                "top_detail_warnings": [],
                "standard_passes": 0,
                "standard_pass_rate": 0.0,
                "side_reps": 0,
                "side_depth_passes": 0,
                "side_depth_pass_rate": 0.0,
                "side_ipf_proxy_passes": 0,
                "side_ipf_proxy_rate": 0.0,
                "best_rep": None,
                "best_detail_rep": None,
                "best_detail_score": None,
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
                "average_detail_score": 0.0,
                "average_detail_coverage": 0.0,
                "average_front_physique_score": None,
                "average_side_ipf_score": None,
                "detail_component_averages": {},
                "top_detail_deductions": [],
                "phase_score_averages": {},
                "phase_coverage_averages": {},
                "phase_confidence_counts": {},
                "phase_deduction_summary": {},
                "weakest_phase": None,
                "detail_watch_reps": 0,
                "detail_watch_rate": 0.0,
                "detail_watch_events": 0,
                "detail_review_events": 0,
                "detail_clear_reps": 0,
                "top_detail_warning": "NONE",
                "top_detail_warnings": [],
                "standard_passes": 0,
                "standard_pass_rate": 0.0,
                "side_reps": 0,
                "side_depth_passes": 0,
                "side_depth_pass_rate": 0.0,
                "side_ipf_proxy_passes": 0,
                "side_ipf_proxy_rate": 0.0,
                "best_rep": None,
                "best_detail_rep": None,
                "best_detail_score": None,
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

        detail_scores = [
            rep.get(
                "detail_score"
            )
            for rep in valid_reps
            if rep.get(
                "detail_score"
            ) is not None
        ]

        average_detail_score = (
            mean(
                detail_scores
            )
            if detail_scores
            else 0.0
        )

        detail_coverages = [
            float(
                rep.get(
                    "detail_coverage",
                    0.0
                )
            )
            for rep in valid_reps
            if rep.get(
                "detail_score"
            ) is not None
        ]

        average_detail_coverage = (
            mean(
                detail_coverages
            )
            if detail_coverages
            else 0.0
        )

        front_physique_scores = [
            rep.get(
                "competition_lenses",
                {}
            ).get(
                "physique_control",
                {}
            ).get(
                "score"
            )
            for rep in valid_reps
            if (
                rep.get(
                    "view"
                ) == "FRONT"
                and rep.get(
                    "competition_lenses",
                    {}
                ).get(
                    "physique_control",
                    {}
                ).get(
                    "score"
                ) is not None
            )
        ]

        side_ipf_scores = [
            rep.get(
                "competition_lenses",
                {}
            ).get(
                "ipf_squat_proxy",
                {}
            ).get(
                "score"
            )
            for rep in valid_reps
            if (
                rep.get(
                    "view"
                ) == "SIDE"
                and rep.get(
                    "competition_lenses",
                    {}
                ).get(
                    "ipf_squat_proxy",
                    {}
                ).get(
                    "score"
                ) is not None
            )
        ]

        average_front_physique_score = (
            mean(
                front_physique_scores
            )
            if front_physique_scores
            else None
        )

        average_side_ipf_score = (
            mean(
                side_ipf_scores
            )
            if side_ipf_scores
            else None
        )

        detail_component_values = {}

        for rep in valid_reps:
            for key, component in rep.get(
                "detail_weighted_components",
                {}
            ).items():
                score = component.get(
                    "score"
                )

                if score is None:
                    continue

                detail_component_values.setdefault(
                    key,
                    []
                ).append(
                    float(
                        score
                    )
                )

        detail_component_averages = {
            key: round(
                mean(
                    values
                ),
                1
            )
            for key, values
            in detail_component_values.items()
            if values
        }

        detail_deduction_stats = {}

        for rep in valid_reps:
            seen_in_rep = set()

            for deduction in rep.get(
                "detail_deductions",
                []
            ):
                name = deduction.get(
                    "name"
                )
                lost_points = float(
                    deduction.get(
                        "lost_points",
                        0.0
                    )
                )

                if not name:
                    continue

                stats = detail_deduction_stats.setdefault(
                    name,
                    {
                        "total_lost_points": 0.0,
                        "occurrences": 0,
                        "affected_reps": 0,
                    }
                )

                stats[
                    "total_lost_points"
                ] += lost_points
                stats[
                    "occurrences"
                ] += 1

                if (
                    lost_points > 0.1
                    and name not in seen_in_rep
                ):
                    stats[
                        "affected_reps"
                    ] += 1
                    seen_in_rep.add(
                        name
                    )

        top_detail_deductions = sorted(
            (
                {
                    "name": name,
                    "total_lost_points": round(
                        stats[
                            "total_lost_points"
                        ],
                        2
                    ),
                    "average_lost_points": round(
                        stats[
                            "total_lost_points"
                        ]
                        / max(
                            stats[
                                "occurrences"
                            ],
                            1
                        ),
                        2
                    ),
                    "affected_reps": stats[
                        "affected_reps"
                    ],
                    "occurrences": stats[
                        "occurrences"
                    ],
                }
                for name, stats
                in detail_deduction_stats.items()
            ),
            key=lambda item: (
                -item[
                    "total_lost_points"
                ],
                item[
                    "name"
                ]
            )
        )[:5]

        phase_score_values = {
            "descent": [],
            "bottom": [],
            "ascent": [],
        }
        phase_coverage_values = {
            "descent": [],
            "bottom": [],
            "ascent": [],
        }
        phase_confidence_counts = {
            "descent": Counter(),
            "bottom": Counter(),
            "ascent": Counter(),
        }

        comparable_phase_reps = [rep for rep in valid_reps if all(
            rep.get("phase_scores", {}).get(phase, {}).get("score") is not None
            and rep.get("phase_scores", {}).get(phase, {}).get("confidence", "LOW") in ("MEDIUM", "HIGH")
            for phase in ("descent", "bottom", "ascent")
        )]
        for rep in comparable_phase_reps:
            for phase, phase_data in rep.get(
                "phase_scores",
                {}
            ).items():
                score = phase_data.get(
                    "score"
                )

                if (
                    phase in phase_score_values
                    and score is not None
                ):
                    phase_score_values[
                        phase
                    ].append(
                        float(
                            score
                        )
                    )

                    coverage = phase_data.get(
                        "coverage"
                    )

                    if coverage is not None:
                        phase_coverage_values[
                            phase
                        ].append(
                            float(
                                coverage
                            )
                        )

                    confidence = phase_data.get(
                        "confidence"
                    )

                    if confidence:
                        phase_confidence_counts[
                            phase
                        ][
                            confidence
                        ] += 1

        phase_score_averages = {
            phase: round(
                mean(
                    values
                ),
                1
            )
            for phase, values
            in phase_score_values.items()
            if values
        }

        phase_coverage_averages = {
            phase: round(
                mean(
                    values
                ),
                3
            )
            for phase, values
            in phase_coverage_values.items()
            if values
        }

        phase_confidence_summary = {}

        confidence_priority = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        }

        for phase, counts in phase_confidence_counts.items():
            if not counts:
                continue

            label = sorted(
                counts.items(),
                key=lambda item: (
                    -item[
                        1
                    ],
                    confidence_priority.get(
                        item[
                            0
                        ],
                        99
                    )
                )
            )[0][0]

            phase_confidence_summary[
                phase
            ] = {
                "label": label,
                "counts": dict(
                    counts
                )
            }

        phase_deduction_stats = {
            "descent": {},
            "bottom": {},
            "ascent": {},
        }

        for rep in comparable_phase_reps:
            for phase, phase_data in rep.get(
                "phase_scores",
                {}
            ).items():
                if phase not in phase_deduction_stats:
                    continue

                for deduction in phase_data.get(
                    "deductions",
                    []
                ):
                    name = deduction.get(
                        "name"
                    )
                    lost_points = float(
                        deduction.get(
                            "lost_points",
                            0.0
                        )
                    )

                    if not name:
                        continue

                    stats = phase_deduction_stats[
                        phase
                    ].setdefault(
                        name,
                        {
                            "total_lost_points": 0.0,
                            "occurrences": 0,
                        }
                    )

                    stats[
                        "total_lost_points"
                    ] += lost_points
                    stats[
                        "occurrences"
                    ] += 1

        phase_deduction_summary = {}

        for phase, components in phase_deduction_stats.items():
            if not components:
                continue

            ranked = sorted(
                (
                    {
                        "name": name,
                        "total_lost_points": round(
                            stats[
                                "total_lost_points"
                            ],
                            2
                        ),
                        "average_lost_points": round(
                            stats[
                                "total_lost_points"
                            ]
                            / max(
                                stats[
                                    "occurrences"
                                ],
                                1
                            ),
                            2
                        ),
                        "occurrences": stats[
                            "occurrences"
                        ],
                    }
                    for name, stats
                    in components.items()
                ),
                key=lambda item: (
                    -item[
                        "total_lost_points"
                    ],
                    item[
                        "name"
                    ]
                )
            )

            phase_deduction_summary[
                phase
            ] = ranked[
                :3
            ]

        weakest_phase = (
            min(
                phase_score_averages.items(),
                key=lambda item: item[
                    1
                ]
            )
            if phase_score_averages
            else None
        )

        weakest_phase_summary = (
            {
                "phase": weakest_phase[
                    0
                ],
                "score": weakest_phase[
                    1
                ],
                "coverage": phase_coverage_averages.get(
                    weakest_phase[
                        0
                    ]
                ),
                "confidence": phase_confidence_summary.get(
                    weakest_phase[
                        0
                    ],
                    {}
                ).get(
                    "label"
                ),
            }
            if weakest_phase is not None
            else None
        )

        detail_watch_reps = sum(
            1
            for rep in valid_reps
            if rep.get(
                "detail_warnings",
                []
            )
        )

        detail_watch_rate = (
            detail_watch_reps
            / len(
                valid_reps
            )
            * 100.0
        )

        detail_warning_counter = Counter()

        for rep in valid_reps:
            detail_warning_counter.update(
                rep.get(
                    "detail_warnings",
                    []
                )
            )

        top_detail_warning = (
            detail_warning_counter.most_common(
                1
            )[0][0]
            if detail_warning_counter
            else "NONE"
        )

        detail_state_counter = Counter()
        detail_warning_breakdown = {}

        for rep in valid_reps:
            checks = rep.get(
                "detail_checks",
                {}
            )

            for warning in rep.get(
                "detail_warnings",
                []
            ):
                state = checks.get(
                    warning,
                    {}
                ).get(
                    "state",
                    "WATCH"
                )

                if state not in (
                    "WATCH",
                    "REVIEW"
                ):
                    state = "WATCH"

                detail_state_counter[
                    state
                ] += 1

                if warning not in detail_warning_breakdown:
                    detail_warning_breakdown[
                        warning
                    ] = {
                        "watch": 0,
                        "review": 0,
                        "total": 0
                    }

                detail_warning_breakdown[
                    warning
                ][
                    state.lower()
                ] += 1
                detail_warning_breakdown[
                    warning
                ][
                    "total"
                ] += 1

        top_detail_warnings = sorted(
            (
                {
                    "name": name,
                    **counts
                }
                for name, counts
                in detail_warning_breakdown.items()
            ),
            key=lambda item: (
                -item[
                    "review"
                ],
                -item[
                    "total"
                ],
                item[
                    "name"
                ]
            )
        )[:3]

        detail_clear_reps = sum(
            1
            for rep in valid_reps
            if not rep.get(
                "detail_warnings",
                []
            )
        )

        standard_passes = sum(
            1
            for rep in valid_reps
            if rep.get(
                "standard_met",
                False
            )
        )

        standard_pass_rate = (
            standard_passes
            / len(
                valid_reps
            )
            * 100.0
        )

        side_reps = [
            rep
            for rep in valid_reps
            if rep.get(
                "view"
            ) == "SIDE"
        ]

        side_depth_passes = sum(
            1
            for rep in side_reps
            if rep.get(
                "depth_standard_met",
                False
            )
        )

        side_ipf_proxy_passes = sum(
            1
            for rep in side_reps
            if rep.get(
                "ipf_depth_proxy_met",
                False
            )
        )

        side_depth_pass_rate = (
            side_depth_passes
            / len(
                side_reps
            )
            * 100.0
            if side_reps
            else 0.0
        )

        side_ipf_proxy_rate = (
            side_ipf_proxy_passes
            / len(
                side_reps
            )
            * 100.0
            if side_reps
            else 0.0
        )

        best_rep = max(
            valid_reps,
            key=lambda rep: rep[
                "quality_score"
            ]
        )

        detail_ranked_reps = [
            rep
            for rep in valid_reps
            if rep.get(
                "detail_score"
            ) is not None
            and rep.get("detail_confidence", "LOW") in ("MEDIUM", "HIGH")
        ]

        best_detail_rep = (
            max(
                detail_ranked_reps,
                key=lambda rep: rep[
                    "detail_score"
                ]
            )
            if detail_ranked_reps
            else None
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
            "average_detail_score": round(
                average_detail_score,
                1
            ),
            "average_detail_coverage": round(
                average_detail_coverage,
                3
            ),
            "average_front_physique_score": (
                round(
                    average_front_physique_score,
                    1
                )
                if average_front_physique_score
                is not None
                else None
            ),
            "average_side_ipf_score": (
                round(
                    average_side_ipf_score,
                    1
                )
                if average_side_ipf_score
                is not None
                else None
            ),
            "detail_component_averages": detail_component_averages,
            "top_detail_deductions": top_detail_deductions,
            "phase_comparable_reps": len(comparable_phase_reps),
            "phase_excluded_reps": len(valid_reps) - len(comparable_phase_reps),
            "phase_score_averages": phase_score_averages,
            "phase_coverage_averages": phase_coverage_averages,
            "phase_confidence_counts": phase_confidence_summary,
            "phase_deduction_summary": phase_deduction_summary,
            "weakest_phase": weakest_phase_summary,
            "detail_watch_reps": detail_watch_reps,
            "detail_watch_rate": round(
                detail_watch_rate,
                1
            ),
            "detail_watch_events": detail_state_counter[
                "WATCH"
            ],
            "detail_review_events": detail_state_counter[
                "REVIEW"
            ],
            "detail_clear_reps": detail_clear_reps,
            "top_detail_warning": top_detail_warning,
            "top_detail_warnings": top_detail_warnings,
            "standard_passes": standard_passes,
            "standard_pass_rate": round(
                standard_pass_rate,
                1
            ),
            "side_reps": len(
                side_reps
            ),
            "side_depth_passes": side_depth_passes,
            "side_depth_pass_rate": round(
                side_depth_pass_rate,
                1
            ),
            "side_ipf_proxy_passes": side_ipf_proxy_passes,
            "side_ipf_proxy_rate": round(
                side_ipf_proxy_rate,
                1
            ),
            "best_rep": best_rep.get(
                "rep"
            ),
            "best_detail_rep": (
                best_detail_rep.get(
                    "rep"
                )
                if best_detail_rep
                else None
            ),
            "best_detail_score": (
                round(
                    best_detail_rep.get(
                        "detail_score"
                    ),
                    1
                )
                if best_detail_rep
                else None
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
