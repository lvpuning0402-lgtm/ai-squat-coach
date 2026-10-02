from feedback.capture_quality import assess_evidence, weakest_confidence
from standards.competition_profiles import (
    COMPETITION_LENSES,
    CONTINUOUS_SCORING,
    DETAIL_GRADE_BANDS,
    DETAIL_PROFILE_NAME,
    DETAIL_PROFILE_VERSION,
    DETAIL_TOLERANCE,
    DETAIL_WEIGHTS,
    PHASE_DETAIL_WEIGHTS,
    PHASE_TOLERANCE,
)
from standards.squat_standard import VISION_TOLERANCE


class CompetitionDetailEvaluator:
    """
    Secondary movement-quality evaluation.

    The hard GENERAL_STRENGTH pass/fail standard is kept separate from this
    weighted detail layer. The weights and continuous score curves are project
    coaching heuristics, not official federation judging sheets.
    """

    @staticmethod
    def _safe(
        value,
        default=None
    ):
        if value is None:
            return default

        try:
            return float(
                value
            )
        except (
            TypeError,
            ValueError
        ):
            return default

    @staticmethod
    def _clamp(
        value,
        low=0.0,
        high=100.0
    ):
        return max(
            low,
            min(
                high,
                value
            )
        )

    @staticmethod
    def _lower_state(
        value,
        good_max,
        review_min
    ):
        if value is None:
            return "INFO"

        if value <= good_max:
            return "PASS"

        if value >= review_min:
            return "REVIEW"

        return "WATCH"

    @staticmethod
    def _higher_state(
        value,
        pass_min,
        review_below
    ):
        if value is None:
            return "INFO"

        if value >= pass_min:
            return "PASS"

        if value < review_below:
            return "REVIEW"

        return "WATCH"

    @staticmethod
    def _boolean_state(
        value
    ):
        if value is None:
            return "INFO"

        return (
            "PASS"
            if bool(
                value
            )
            else "REVIEW"
        )

    @classmethod
    def _lower_score(
        cls,
        value,
        good_max,
        review_min
    ):
        if value is None:
            return None

        pass_floor = CONTINUOUS_SCORING[
            "pass_floor"
        ]
        watch_floor = CONTINUOUS_SCORING[
            "watch_floor"
        ]
        review_floor = CONTINUOUS_SCORING[
            "review_floor"
        ]

        if value <= good_max:
            if good_max <= 0:
                return 100.0

            progress = cls._clamp(
                value
                / good_max,
                0.0,
                1.0
            )

            return round(
                100.0
                - (
                    100.0
                    - pass_floor
                )
                * progress,
                1
            )

        transition = max(
            review_min
            - good_max,
            0.001
        )

        if value < review_min:
            progress = (
                value
                - good_max
            ) / transition

            return round(
                pass_floor
                - (
                    pass_floor
                    - watch_floor
                )
                * progress,
                1
            )

        excess = (
            value
            - review_min
        ) / transition

        review_ceiling = (
            watch_floor
            - 0.1
        )

        return round(
            cls._clamp(
                review_ceiling
                - (
                    review_ceiling
                    - review_floor
                )
                * min(
                    excess,
                    1.0
                ),
                review_floor,
                review_ceiling
            ),
            1
        )

    @classmethod
    def _higher_score(
        cls,
        value,
        pass_min,
        review_below
    ):
        if value is None:
            return None

        pass_floor = CONTINUOUS_SCORING[
            "pass_floor"
        ]
        watch_floor = CONTINUOUS_SCORING[
            "watch_floor"
        ]
        review_floor = CONTINUOUS_SCORING[
            "review_floor"
        ]

        transition = max(
            pass_min
            - review_below,
            0.001
        )

        if value >= pass_min:
            surplus = min(
                (
                    value
                    - pass_min
                )
                / transition,
                1.0
            )

            return round(
                pass_floor
                + (
                    100.0
                    - pass_floor
                )
                * surplus,
                1
            )

        if value >= review_below:
            progress = (
                value
                - review_below
            ) / transition

            return round(
                watch_floor
                + (
                    pass_floor
                    - watch_floor
                )
                * progress,
                1
            )

        deficit = (
            review_below
            - value
        ) / transition

        return round(
            cls._clamp(
                watch_floor
                - (
                    watch_floor
                    - review_floor
                )
                * min(
                    deficit,
                    1.0
                ),
                review_floor,
                watch_floor
            ),
            1
        )

    @staticmethod
    def _boolean_score(
        value
    ):
        if value is None:
            return None

        return (
            100.0
            if bool(
                value
            )
            else 60.0
        )

    @staticmethod
    def _detail_grade(
        score
    ):
        if score is None:
            return "N/A"

        for minimum, grade in DETAIL_GRADE_BANDS:
            if score >= minimum:
                return grade

        return "E"

    @staticmethod
    def _detail_label(
        score
    ):
        if score is None:
            return "INFO"

        if score >= 90.0:
            return "EXCELLENT"

        if score >= 80.0:
            return "STRONG"

        if score >= 70.0:
            return "WATCH"

        return "REVIEW"

    @staticmethod
    def _item(
        state,
        score=None,
        value=None,
        unit=None,
        lens=None,
        note=None
    ):
        return {
            "state": state,
            "score": (
                round(
                    score,
                    1
                )
                if score is not None
                else None
            ),
            "value": (
                round(
                    value,
                    3
                )
                if isinstance(
                    value,
                    float
                )
                else value
            ),
            "unit": unit,
            "lens": lens,
            "note": note,
        }

    @staticmethod
    def _weight_coverage(
        checks,
        weights
    ):
        configured = sum(
            float(
                weight
            )
            for weight in weights.values()
        )

        if configured <= 0:
            return 0.0

        available = sum(
            float(
                weight
            )
            for key, weight
            in weights.items()
            if checks.get(
                key,
                {}
            ).get(
                "score"
            ) is not None
        )

        return round(
            available
            / configured,
            3
        )

    @staticmethod
    def _coverage_confidence(
        coverage,
        samples=None,
        phase=None
    ):
        if coverage < 0.70:
            return "LOW"

        if samples is None:
            return (
                "HIGH"
                if coverage >= 0.90
                else "MEDIUM"
            )

        if samples < 2:
            return "LOW"

        high_sample_min = (
            2
            if phase == "bottom"
            else 4
        )

        if (
            coverage >= 0.90
            and samples >= high_sample_min
        ):
            return "HIGH"

        return "MEDIUM"

    @staticmethod
    def _weighted_score(
        checks,
        weights
    ):
        available = []

        for key, weight in weights.items():
            score = checks.get(
                key,
                {}
            ).get(
                "score"
            )

            if score is None:
                continue

            available.append(
                (
                    float(
                        score
                    ),
                    float(
                        weight
                    )
                )
            )

        if not available:
            return (
                None,
                {}
            )

        total_weight = sum(
            weight
            for _,
            weight in available
        )

        if total_weight <= 0:
            return (
                None,
                {}
            )

        components = {}
        weighted_total = 0.0

        for key, weight in weights.items():
            score = checks.get(
                key,
                {}
            ).get(
                "score"
            )

            if score is None:
                continue

            normalized_weight = (
                float(
                    weight
                )
                / total_weight
            )

            contribution = (
                float(
                    score
                )
                * normalized_weight
            )

            weighted_total += contribution

            max_contribution = (
                100.0
                * normalized_weight
            )

            lost_points = max(
                0.0,
                max_contribution
                - contribution
            )

            components[
                key
            ] = {
                "score": round(
                    float(
                        score
                    ),
                    1
                ),
                "weight": round(
                    normalized_weight,
                    3
                ),
                "max_contribution": round(
                    max_contribution,
                    2
                ),
                "contribution": round(
                    contribution,
                    2
                ),
                "lost_points": round(
                    lost_points,
                    2
                )
            }

        return (
            round(
                weighted_total,
                1
            ),
            components
        )

    @staticmethod
    def _deductions(
        components,
        limit=None
    ):
        deductions = [
            {
                "name": key,
                "score": data.get(
                    "score"
                ),
                "weight": data.get(
                    "weight"
                ),
                "lost_points": data.get(
                    "lost_points",
                    0.0
                ),
            }
            for key, data
            in components.items()
            if data.get(
                "lost_points",
                0.0
            ) > 0.01
        ]

        deductions.sort(
            key=lambda item: (
                -item[
                    "lost_points"
                ],
                item[
                    "name"
                ]
            )
        )

        if limit is not None:
            return deductions[
                :limit
            ]

        return deductions

    @staticmethod
    def _phase_warnings(
        checks
    ):
        return [
            key
            for key, item
            in checks.items()
            if item.get(
                "state"
            ) in (
                "WATCH",
                "REVIEW",
            )
        ]

    def _front_phase_scores(
        self,
        rep
    ):
        phase_metrics = rep.get(
            "phase_metrics",
            {}
        )

        results = {}

        knee_good = VISION_TOLERANCE[
            "knee_in_good_max"
        ]
        knee_review = VISION_TOLERANCE[
            "knee_in_bad_min"
        ]
        sync_good = VISION_TOLERANCE[
            "ascent_progress_good_max"
        ]
        sync_review = VISION_TOLERANCE[
            "ascent_progress_bad_min"
        ]

        for phase in (
            "descent",
            "bottom",
            "ascent",
        ):
            metrics = phase_metrics.get(
                phase,
                {}
            )

            if metrics.get(
                "samples",
                0
            ) <= 0:
                continue

            left_inward = self._safe(
                metrics.get(
                    "max_left_inward"
                )
            )
            right_inward = self._safe(
                metrics.get(
                    "max_right_inward"
                )
            )

            inward_values = [
                value
                for value in (
                    left_inward,
                    right_inward
                )
                if value is not None
            ]

            max_inward = (
                max(
                    inward_values
                )
                if inward_values
                else None
            )

            head = self._safe(
                metrics.get(
                    "max_head_shift"
                )
            )
            shoulder = self._safe(
                metrics.get(
                    "max_shoulder_tilt"
                )
            )
            hip_tilt = self._safe(
                metrics.get(
                    "max_hip_tilt"
                )
            )
            center = self._safe(
                metrics.get(
                    "max_center_shift"
                )
            )
            knee_asymmetry = self._safe(
                metrics.get(
                    "max_knee_angle_asymmetry"
                )
            )
            knee_height_symmetry = self._safe(
                metrics.get(
                    "max_symmetry_value"
                )
            )
            ascent_sync = self._safe(
                metrics.get(
                    "max_ascent_sync_error"
                )
            )

            checks = {
                "knee_tracking": self._item(
                    self._lower_state(
                        max_inward,
                        knee_good,
                        knee_review
                    ),
                    self._lower_score(
                        max_inward,
                        knee_good,
                        knee_review
                    ),
                    max_inward,
                    "hip_width_ratio",
                    "GENERAL_STRENGTH",
                    "Phase-specific knee tracking."
                ),
                "shoulder_level": self._item(
                    self._lower_state(
                        shoulder,
                        DETAIL_TOLERANCE[
                            "shoulder_tilt_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "shoulder_tilt_review_min"
                        ]
                    ),
                    self._lower_score(
                        shoulder,
                        DETAIL_TOLERANCE[
                            "shoulder_tilt_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "shoulder_tilt_review_min"
                        ]
                    ),
                    shoulder,
                    "shoulder_width_ratio",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific shoulder level."
                ),
                "hip_level": self._item(
                    self._lower_state(
                        hip_tilt,
                        DETAIL_TOLERANCE[
                            "hip_tilt_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "hip_tilt_review_min"
                        ]
                    ),
                    self._lower_score(
                        hip_tilt,
                        DETAIL_TOLERANCE[
                            "hip_tilt_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "hip_tilt_review_min"
                        ]
                    ),
                    hip_tilt,
                    "hip_width_ratio",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific pelvis level."
                ),
                "center_balance": self._item(
                    self._lower_state(
                        center,
                        DETAIL_TOLERANCE[
                            "center_shift_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "center_shift_review_min"
                        ]
                    ),
                    self._lower_score(
                        center,
                        DETAIL_TOLERANCE[
                            "center_shift_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "center_shift_review_min"
                        ]
                    ),
                    center,
                    "shoulder_width_ratio",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific lateral balance."
                ),
                "head_control": self._item(
                    self._lower_state(
                        head,
                        DETAIL_TOLERANCE[
                            "head_shift_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "head_shift_review_min"
                        ]
                    ),
                    self._lower_score(
                        head,
                        DETAIL_TOLERANCE[
                            "head_shift_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "head_shift_review_min"
                        ]
                    ),
                    head,
                    "shoulder_width_ratio",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific head control."
                ),
                "knee_angle_symmetry": self._item(
                    self._lower_state(
                        knee_asymmetry,
                        DETAIL_TOLERANCE[
                            "knee_angle_asym_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "knee_angle_asym_review_min"
                        ]
                    ),
                    self._lower_score(
                        knee_asymmetry,
                        DETAIL_TOLERANCE[
                            "knee_angle_asym_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "knee_angle_asym_review_min"
                        ]
                    ),
                    knee_asymmetry,
                    "deg",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific left/right knee-angle symmetry."
                ),
                "knee_height_symmetry": self._item(
                    self._lower_state(
                        knee_height_symmetry,
                        DETAIL_TOLERANCE[
                            "front_symmetry_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "front_symmetry_review_min"
                        ]
                    ),
                    self._lower_score(
                        knee_height_symmetry,
                        DETAIL_TOLERANCE[
                            "front_symmetry_good_max"
                        ],
                        DETAIL_TOLERANCE[
                            "front_symmetry_review_min"
                        ]
                    ),
                    knee_height_symmetry,
                    "hip_width_ratio",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific knee-height symmetry."
                ),
            }

            if phase == "ascent":
                checks[
                    "ascent_control"
                ] = self._item(
                    self._lower_state(
                        ascent_sync,
                        sync_good,
                        sync_review
                    ),
                    self._lower_score(
                        ascent_sync,
                        sync_good,
                        sync_review
                    ),
                    ascent_sync,
                    "progress_delta",
                    "GENERAL_STRENGTH",
                    "Phase-specific shoulder/hip ascent coordination."
                )

            phase_weights = PHASE_DETAIL_WEIGHTS[
                "FRONT"
            ][
                phase
            ]

            score, components = self._weighted_score(
                checks,
                phase_weights
            )

            coverage = self._weight_coverage(
                checks,
                phase_weights
            )
            samples = metrics.get(
                "samples",
                0
            )

            results[
                phase
            ] = {
                "score": score,
                "grade": self._detail_grade(
                    score
                ),
                "label": self._detail_label(
                    score
                ),
                "checks": checks,
                "weighted_components": components,
                "deductions": self._deductions(
                    components
                ),
                "warnings": self._phase_warnings(
                    checks
                ),
                "coverage": coverage,
                "confidence": self._coverage_confidence(
                    coverage,
                    samples=samples,
                    phase=phase
                ),
                "samples": samples,
            }

        return results

    def _side_phase_scores(
        self,
        rep
    ):
        phase_metrics = rep.get(
            "phase_metrics",
            {}
        )

        results = {}

        sync_good = VISION_TOLERANCE[
            "ascent_progress_good_max"
        ]
        sync_review = VISION_TOLERANCE[
            "ascent_progress_bad_min"
        ]
        head_good = DETAIL_TOLERANCE[
            "side_head_forward_good_max"
        ]
        head_review = DETAIL_TOLERANCE[
            "side_head_forward_review_min"
        ]
        lockout_good = DETAIL_TOLERANCE[
            "side_lockout_good_min"
        ]
        lockout_review = DETAIL_TOLERANCE[
            "side_lockout_review_below"
        ]

        for phase in (
            "descent",
            "bottom",
            "ascent",
        ):
            metrics = phase_metrics.get(
                phase,
                {}
            )

            if metrics.get(
                "samples",
                0
            ) <= 0:
                continue

            head = self._safe(
                metrics.get(
                    "max_head_forward"
                )
            )
            min_trunk = self._safe(
                metrics.get(
                    "min_trunk_lean"
                )
            )
            max_trunk = self._safe(
                metrics.get(
                    "max_trunk_lean"
                )
            )

            trunk_range = (
                max(
                    0.0,
                    max_trunk
                    - min_trunk
                )
                if (
                    min_trunk is not None
                    and max_trunk is not None
                )
                else None
            )

            checks = {
                "head_control": self._item(
                    self._lower_state(
                        head,
                        head_good,
                        head_review
                    ),
                    self._lower_score(
                        head,
                        head_good,
                        head_review
                    ),
                    head,
                    "torso_length_ratio",
                    "PHYSIQUE_CONTROL_LENS",
                    "Phase-specific head/posture control."
                ),
                "trunk_stability": self._item(
                    self._lower_state(
                        trunk_range,
                        PHASE_TOLERANCE[
                            "trunk_range_good_max"
                        ],
                        PHASE_TOLERANCE[
                            "trunk_range_review_min"
                        ]
                    ),
                    self._lower_score(
                        trunk_range,
                        PHASE_TOLERANCE[
                            "trunk_range_good_max"
                        ],
                        PHASE_TOLERANCE[
                            "trunk_range_review_min"
                        ]
                    ),
                    trunk_range,
                    "deg_range",
                    "ANGLE_STABILITY_HEURISTIC",
                    (
                        "Change in trunk lean within this phase; "
                        "not an absolute torso-angle rule."
                    )
                ),
            }

            if phase == "bottom":
                depth_margin = self._safe(
                    metrics.get(
                        "max_depth_margin"
                    )
                )

                depth_ok = (
                    depth_margin is not None
                    and depth_margin
                    >= VISION_TOLERANCE[
                        "general_depth_margin_min"
                    ]
                )

                checks[
                    "general_depth"
                ] = self._item(
                    self._boolean_state(
                        depth_ok
                    ),
                    self._boolean_score(
                        depth_ok
                    ),
                    depth_margin,
                    "thigh_length_ratio",
                    "GENERAL_STRENGTH",
                    "Depth reached in the bottom phase."
                )

            if phase == "ascent":
                ascent_sync = self._safe(
                    metrics.get(
                        "max_ascent_sync_error"
                    )
                )
                lockout = self._safe(
                    metrics.get(
                        "max_knee_angle"
                    )
                )

                checks[
                    "ascent_control"
                ] = self._item(
                    self._lower_state(
                        ascent_sync,
                        sync_good,
                        sync_review
                    ),
                    self._lower_score(
                        ascent_sync,
                        sync_good,
                        sync_review
                    ),
                    ascent_sync,
                    "progress_delta",
                    "GENERAL_STRENGTH",
                    "Phase-specific shoulder/hip ascent coordination."
                )
                checks[
                    "lockout_proxy"
                ] = self._item(
                    self._higher_state(
                        lockout,
                        lockout_good,
                        lockout_review
                    ),
                    self._higher_score(
                        lockout,
                        lockout_good,
                        lockout_review
                    ),
                    lockout,
                    "deg",
                    "IPF_SQUAT_PROXY",
                    "Return-to-upright knee-extension proxy."
                )

            phase_weights = PHASE_DETAIL_WEIGHTS[
                "SIDE"
            ][
                phase
            ]

            score, components = self._weighted_score(
                checks,
                phase_weights
            )

            coverage = self._weight_coverage(
                checks,
                phase_weights
            )
            samples = metrics.get(
                "samples",
                0
            )

            results[
                phase
            ] = {
                "score": score,
                "grade": self._detail_grade(
                    score
                ),
                "label": self._detail_label(
                    score
                ),
                "checks": checks,
                "weighted_components": components,
                "deductions": self._deductions(
                    components
                ),
                "warnings": self._phase_warnings(
                    checks
                ),
                "coverage": coverage,
                "confidence": self._coverage_confidence(
                    coverage,
                    samples=samples,
                    phase=phase
                ),
                "samples": samples,
                "angle_snapshot": {
                    "min_knee_angle_deg": self._safe(
                        metrics.get(
                            "min_knee_angle"
                        )
                    ),
                    "min_hip_angle_deg": self._safe(
                        metrics.get(
                            "min_hip_angle"
                        )
                    ),
                    "trunk_range_deg": (
                        round(
                            trunk_range,
                            1
                        )
                        if trunk_range is not None
                        else None
                    ),
                    "max_shin_angle_deg": self._safe(
                        metrics.get(
                            "max_shin_angle"
                        )
                    ),
                },
            }

        return results

    @staticmethod
    def _weakest_phase(
        phase_scores
    ):
        available = [
            (
                phase,
                data.get(
                    "score"
                )
            )
            for phase, data
            in phase_scores.items()
            if data.get(
                "score"
            ) is not None
        ]

        # A weakest phase requires comparable evidence from all three phases.
        if len(available) != 3 or any(
            data.get("confidence", "LOW") == "LOW"
            for data in phase_scores.values()
        ):
            return None

        phase, score = min(
            available,
            key=lambda item: item[
                1
            ]
        )

        return {
            "phase": phase,
            "score": round(
                score,
                1
            ),
        }

    def _front(
        self,
        rep
    ):
        head = self._safe(
            rep.get(
                "max_head_shift"
            )
        )
        shoulder = self._safe(
            rep.get(
                "max_shoulder_tilt"
            )
        )
        hip_tilt = self._safe(
            rep.get(
                "max_hip_tilt"
            )
        )
        center = self._safe(
            rep.get(
                "max_center_shift"
            )
        )
        knee_asymmetry = self._safe(
            rep.get(
                "max_knee_angle_asymmetry"
            )
        )
        knee_height_symmetry = self._safe(
            rep.get(
                "max_symmetry_value"
            )
        )
        sync = self._safe(
            rep.get(
                "max_ascent_sync_error",
                rep.get(
                    "max_sync_error"
                )
            )
        )

        left_inward = self._safe(
            rep.get(
                "max_left_inward",
                rep.get(
                    "left_inward"
                )
            ),
            0.0
        )
        right_inward = self._safe(
            rep.get(
                "max_right_inward",
                rep.get(
                    "right_inward"
                )
            ),
            0.0
        )

        max_inward = max(
            0.0,
            left_inward,
            right_inward
        )

        knee_good = VISION_TOLERANCE[
            "knee_in_good_max"
        ]
        knee_review = VISION_TOLERANCE[
            "knee_in_bad_min"
        ]

        sync_good = VISION_TOLERANCE[
            "ascent_progress_good_max"
        ]
        sync_review = VISION_TOLERANCE[
            "ascent_progress_bad_min"
        ]

        checks = {
            "knee_tracking": self._item(
                self._lower_state(
                    max_inward,
                    knee_good,
                    knee_review
                ),
                self._lower_score(
                    max_inward,
                    knee_good,
                    knee_review
                ),
                max_inward,
                "hip_width_ratio",
                "GENERAL_STRENGTH",
                "Knees relative to feet/toes."
            ),
            "ascent_control": self._item(
                self._lower_state(
                    sync,
                    sync_good,
                    sync_review
                ),
                self._lower_score(
                    sync,
                    sync_good,
                    sync_review
                ),
                sync,
                "progress_delta",
                "GENERAL_STRENGTH",
                "Shoulder and hip progress during ascent."
            ),
            "shoulder_level": self._item(
                self._lower_state(
                    shoulder,
                    DETAIL_TOLERANCE[
                        "shoulder_tilt_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "shoulder_tilt_review_min"
                    ]
                ),
                self._lower_score(
                    shoulder,
                    DETAIL_TOLERANCE[
                        "shoulder_tilt_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "shoulder_tilt_review_min"
                    ]
                ),
                shoulder,
                "shoulder_width_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Secondary symmetry / presentation-control heuristic."
            ),
            "hip_level": self._item(
                self._lower_state(
                    hip_tilt,
                    DETAIL_TOLERANCE[
                        "hip_tilt_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "hip_tilt_review_min"
                    ]
                ),
                self._lower_score(
                    hip_tilt,
                    DETAIL_TOLERANCE[
                        "hip_tilt_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "hip_tilt_review_min"
                    ]
                ),
                hip_tilt,
                "hip_width_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Secondary balance / symmetry heuristic."
            ),
            "center_balance": self._item(
                self._lower_state(
                    center,
                    DETAIL_TOLERANCE[
                        "center_shift_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "center_shift_review_min"
                    ]
                ),
                self._lower_score(
                    center,
                    DETAIL_TOLERANCE[
                        "center_shift_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "center_shift_review_min"
                    ]
                ),
                center,
                "shoulder_width_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Lateral body-control heuristic."
            ),
            "head_control": self._item(
                self._lower_state(
                    head,
                    DETAIL_TOLERANCE[
                        "head_shift_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "head_shift_review_min"
                    ]
                ),
                self._lower_score(
                    head,
                    DETAIL_TOLERANCE[
                        "head_shift_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "head_shift_review_min"
                    ]
                ),
                head,
                "shoulder_width_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Head position relative to shoulder center."
            ),
            "knee_angle_symmetry": self._item(
                self._lower_state(
                    knee_asymmetry,
                    DETAIL_TOLERANCE[
                        "knee_angle_asym_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "knee_angle_asym_review_min"
                    ]
                ),
                self._lower_score(
                    knee_asymmetry,
                    DETAIL_TOLERANCE[
                        "knee_angle_asym_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "knee_angle_asym_review_min"
                    ]
                ),
                knee_asymmetry,
                "deg",
                "PHYSIQUE_CONTROL_LENS",
                "Left/right 2D knee-flexion difference."
            ),
            "knee_height_symmetry": self._item(
                self._lower_state(
                    knee_height_symmetry,
                    DETAIL_TOLERANCE[
                        "front_symmetry_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "front_symmetry_review_min"
                    ]
                ),
                self._lower_score(
                    knee_height_symmetry,
                    DETAIL_TOLERANCE[
                        "front_symmetry_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "front_symmetry_review_min"
                    ]
                ),
                knee_height_symmetry,
                "hip_width_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Knee-height symmetry; diagnostic only."
            ),
        }

        front_weights = DETAIL_WEIGHTS[
            "FRONT_COACH"
        ]

        detail_score, weighted_components = (
            self._weighted_score(
                checks,
                front_weights
            )
        )

        detail_coverage = self._weight_coverage(
            checks,
            front_weights
        )

        physique_score, physique_components = (
            self._weighted_score(
                checks,
                DETAIL_WEIGHTS[
                    "PHYSIQUE_CONTROL_FRONT"
                ]
            )
        )

        phase_scores = self._front_phase_scores(
            rep
        )

        return {
            "checks": checks,
            "detail_score": detail_score,
            "detail_grade": self._detail_grade(
                detail_score
            ),
            "detail_label": self._detail_label(
                detail_score
            ),
            "detail_coverage": detail_coverage,
            "detail_confidence": self._coverage_confidence(
                detail_coverage
            ),
            "weighted_components": weighted_components,
            "detail_deductions": self._deductions(
                weighted_components
            ),
            "phase_scores": phase_scores,
            "weakest_phase": self._weakest_phase(
                phase_scores
            ),
            "angle_metrics": {
                "knee_angle_asymmetry_deg": knee_asymmetry,
            },
            "competition_lenses": {
                "physique_control": {
                    "score": physique_score,
                    "grade": self._detail_grade(
                        physique_score
                    ),
                    "components": physique_components,
                    "deductions": self._deductions(
                        physique_components
                    ),
                    "basis": [
                        "symmetry",
                        "balance",
                        "presentation_control",
                    ],
                    "source_profile": (
                        "IFBB/NPC-inspired visual-control lens"
                    ),
                    "official_squat_score": False,
                },
                "ipf_squat_proxy": {
                    "available": False,
                    "reason": (
                        "Front view does not certify competition depth."
                    ),
                },
            },
        }

    def _side(
        self,
        rep
    ):
        depth_general = rep.get(
            "depth_standard_met"
        )
        ipf_depth = rep.get(
            "ipf_depth_proxy_met"
        )

        sync = self._safe(
            rep.get(
                "max_ascent_sync_error",
                rep.get(
                    "max_sync_error"
                )
            )
        )
        head = self._safe(
            rep.get(
                "max_head_forward"
            )
        )
        lockout = self._safe(
            rep.get(
                "max_knee_angle"
            )
        )

        knee_angle = self._safe(
            rep.get(
                "min_knee_angle"
            )
        )
        hip_angle = self._safe(
            rep.get(
                "min_hip_angle"
            )
        )
        trunk = self._safe(
            rep.get(
                "max_trunk_lean"
            )
        )
        shin = self._safe(
            rep.get(
                "shin_angle_at_min_knee"
            )
        )
        depth_margin = self._safe(
            rep.get(
                "max_depth_margin"
            )
        )

        sync_good = VISION_TOLERANCE[
            "ascent_progress_good_max"
        ]
        sync_review = VISION_TOLERANCE[
            "ascent_progress_bad_min"
        ]

        lockout_good = DETAIL_TOLERANCE[
            "side_lockout_good_min"
        ]
        lockout_review = DETAIL_TOLERANCE[
            "side_lockout_review_below"
        ]

        head_good = DETAIL_TOLERANCE[
            "side_head_forward_good_max"
        ]
        head_review = DETAIL_TOLERANCE[
            "side_head_forward_review_min"
        ]

        checks = {
            "general_depth": self._item(
                self._boolean_state(
                    depth_general
                ),
                self._boolean_score(
                    depth_general
                ),
                depth_margin,
                "thigh_length_ratio",
                "GENERAL_STRENGTH",
                "Approximately parallel-or-below landmark proxy."
            ),
            "ascent_control": self._item(
                self._lower_state(
                    sync,
                    sync_good,
                    sync_review
                ),
                self._lower_score(
                    sync,
                    sync_good,
                    sync_review
                ),
                sync,
                "progress_delta",
                "GENERAL_STRENGTH",
                "Shoulder and hip progress during ascent."
            ),
            "head_control": self._item(
                self._lower_state(
                    head,
                    head_good,
                    head_review
                ),
                self._lower_score(
                    head,
                    head_good,
                    head_review
                ),
                head,
                "torso_length_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Secondary posture / presentation-control heuristic."
            ),
            "lockout_proxy": self._item(
                self._higher_state(
                    lockout,
                    lockout_good,
                    lockout_review
                ),
                self._higher_score(
                    lockout,
                    lockout_good,
                    lockout_review
                ),
                lockout,
                "deg",
                "IPF_SQUAT_PROXY",
                (
                    "Webcam knee-extension proxy only; "
                    "not an official locked-knee ruling."
                )
            ),
            "ipf_depth_proxy": self._item(
                self._boolean_state(
                    ipf_depth
                ),
                self._boolean_score(
                    ipf_depth
                ),
                depth_margin,
                "thigh_length_ratio",
                "IPF_SQUAT_PROXY",
                (
                    "Landmark-center proxy for the IPF depth rule; "
                    "not an official referee decision."
                )
            ),
            "knee_flexion_angle": self._item(
                "INFO",
                None,
                knee_angle,
                "deg",
                "ANGLE_DIAGNOSTIC",
                "Descriptive 2D angle; no universal squat cutoff."
            ),
            "hip_flexion_angle": self._item(
                "INFO",
                None,
                hip_angle,
                "deg",
                "ANGLE_DIAGNOSTIC",
                "Descriptive 2D angle; no universal squat cutoff."
            ),
            "trunk_lean_angle": self._item(
                "INFO",
                None,
                trunk,
                "deg",
                "ANGLE_DIAGNOSTIC",
                (
                    "Descriptive only because anthropometry, stance and "
                    "squat style change normal torso angle."
                )
            ),
            "shin_angle": self._item(
                "INFO",
                None,
                shin,
                "deg",
                "ANGLE_DIAGNOSTIC",
                "Shin inclination from vertical at deepest knee flexion."
            ),
        }

        side_weights = DETAIL_WEIGHTS[
            "SIDE_COACH"
        ]

        detail_score, weighted_components = (
            self._weighted_score(
                checks,
                side_weights
            )
        )

        detail_coverage = self._weight_coverage(
            checks,
            side_weights
        )

        ipf_score, ipf_components = (
            self._weighted_score(
                checks,
                DETAIL_WEIGHTS[
                    "IPF_SQUAT_PROXY"
                ]
            )
        )

        physique_score, physique_components = (
            self._weighted_score(
                checks,
                {
                    "head_control": 1.0
                }
            )
        )

        phase_scores = self._side_phase_scores(
            rep
        )

        return {
            "checks": checks,
            "detail_score": detail_score,
            "detail_grade": self._detail_grade(
                detail_score
            ),
            "detail_label": self._detail_label(
                detail_score
            ),
            "detail_coverage": detail_coverage,
            "detail_confidence": self._coverage_confidence(
                detail_coverage
            ),
            "weighted_components": weighted_components,
            "detail_deductions": self._deductions(
                weighted_components
            ),
            "phase_scores": phase_scores,
            "weakest_phase": self._weakest_phase(
                phase_scores
            ),
            "angle_metrics": {
                "min_knee_angle_deg": knee_angle,
                "min_hip_angle_deg": hip_angle,
                "max_trunk_lean_deg": trunk,
                "shin_angle_at_depth_deg": shin,
            },
            "competition_lenses": {
                "ipf_squat_proxy": {
                    "score": ipf_score,
                    "grade": self._detail_grade(
                        ipf_score
                    ),
                    "components": ipf_components,
                    "deductions": self._deductions(
                        ipf_components
                    ),
                    "partial_proxy": True,
                    "official_referee_decision": False,
                },
                "physique_control": {
                    "score": physique_score,
                    "grade": self._detail_grade(
                        physique_score
                    ),
                    "components": physique_components,
                    "deductions": self._deductions(
                        physique_components
                    ),
                    "basis": [
                        "presentation_control",
                    ],
                    "official_squat_score": False,
                },
            },
        }

    def evaluate(
        self,
        rep
    ):
        view = rep.get(
            "view",
            "UNKNOWN"
        )

        if view == "FRONT":
            result = self._front(
                rep
            )
        elif view == "SIDE":
            result = self._side(
                rep
            )
        else:
            result = {
                "checks": {},
                "detail_score": None,
                "detail_grade": "N/A",
                "detail_label": "INFO",
                "detail_coverage": 0.0,
                "detail_confidence": "LOW",
                "weighted_components": {},
                "detail_deductions": [],
                "phase_scores": {},
                "weakest_phase": None,
                "angle_metrics": {},
                "competition_lenses": {},
            }

        evidence = assess_evidence(rep, result)
        result["confidence_breakdown"] = evidence
        result["detail_confidence"] = evidence["overall"]
        result["detail_provisional"] = evidence["overall"] != "HIGH"
        # Capture reliability also bounds every phase, including coach aggregation.
        capture_cap = weakest_confidence([
            "MEDIUM" if evidence[key] == "UNKNOWN" else evidence[key]
            for key in ("pose_quality", "view_quality")
        ])
        for phase in result["phase_scores"].values():
            phase["confidence"] = weakest_confidence([phase["confidence"], capture_cap])
        result["weakest_phase"] = self._weakest_phase(result["phase_scores"])

        warnings = [
            key
            for key, item
            in result[
                "checks"
            ].items()
            if (
                item.get(
                    "state"
                ) in (
                    "WATCH",
                    "REVIEW",
                )
                and item.get(
                    "lens"
                ) != "IPF_SQUAT_PROXY"
            )
        ]

        competition_flags = [
            key
            for key, item
            in result[
                "checks"
            ].items()
            if (
                item.get(
                    "state"
                ) in (
                    "WATCH",
                    "REVIEW",
                )
                and item.get(
                    "lens"
                ) == "IPF_SQUAT_PROXY"
            )
        ]

        return {
            "detail_profile": DETAIL_PROFILE_NAME,
            "detail_profile_version": DETAIL_PROFILE_VERSION,
            "profile_sources": COMPETITION_LENSES,
            **result,
            "detail_warnings": warnings,
            "competition_flags": competition_flags,
        }
