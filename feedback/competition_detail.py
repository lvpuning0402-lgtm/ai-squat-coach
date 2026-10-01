from statistics import mean

from standards.competition_profiles import (
    COMPETITION_LENSES,
    DETAIL_PROFILE_NAME,
    DETAIL_PROFILE_VERSION,
    DETAIL_STATE_SCORE,
    DETAIL_TOLERANCE,
)
from standards.squat_standard import VISION_TOLERANCE


class CompetitionDetailEvaluator:
    """
    Secondary movement-quality evaluation.

    This layer is deliberately separate from the hard squat standard:
    - GENERAL_STRENGTH remains the primary pass/fail profile.
    - IPF is represented only by measurable webcam proxies.
    - IFBB/NPC judging concepts are used only as a symmetry/balance/
      presentation-inspired movement-control lens.
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

    @staticmethod
    def _state_score(
        state
    ):
        return DETAIL_STATE_SCORE.get(
            state
        )

    @classmethod
    def _score_states(
        cls,
        checks
    ):
        scores = [
            cls._state_score(
                item.get(
                    "state"
                )
            )
            for item in checks.values()
        ]

        scores = [
            score
            for score in scores
            if score is not None
        ]

        if not scores:
            return None

        return round(
            mean(
                scores
            ),
            1
        )

    @staticmethod
    def _detail_label(
        score
    ):
        if score is None:
            return "INFO"

        if score >= 92.0:
            return "EXCELLENT"

        if score >= 82.0:
            return "STRONG"

        if score >= 70.0:
            return "WATCH"

        return "REVIEW"

    @staticmethod
    def _item(
        state,
        value=None,
        unit=None,
        lens=None,
        note=None
    ):
        return {
            "state": state,
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

        checks = {
            "knee_tracking": self._item(
                self._lower_state(
                    max_inward,
                    VISION_TOLERANCE[
                        "knee_in_good_max"
                    ],
                    VISION_TOLERANCE[
                        "knee_in_bad_min"
                    ]
                ),
                max_inward,
                "hip_width_ratio",
                "GENERAL_STRENGTH",
                "Knees relative to feet/toes."
            ),
            "ascent_control": self._item(
                self._lower_state(
                    sync,
                    VISION_TOLERANCE[
                        "ascent_progress_good_max"
                    ],
                    VISION_TOLERANCE[
                        "ascent_progress_bad_min"
                    ]
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
                knee_height_symmetry,
                "hip_width_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Knee-height symmetry; diagnostic only."
            ),
        }

        physique_keys = (
            "shoulder_level",
            "hip_level",
            "center_balance",
            "head_control",
            "knee_angle_symmetry",
            "knee_height_symmetry",
        )

        physique_checks = {
            key: checks[
                key
            ]
            for key in physique_keys
        }

        detail_score = self._score_states(
            checks
        )

        return {
            "checks": checks,
            "detail_score": detail_score,
            "detail_label": self._detail_label(
                detail_score
            ),
            "angle_metrics": {
                "knee_angle_asymmetry_deg": knee_asymmetry,
            },
            "competition_lenses": {
                "physique_control": {
                    "score": self._score_states(
                        physique_checks
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

        checks = {
            "general_depth": self._item(
                self._boolean_state(
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
                    VISION_TOLERANCE[
                        "ascent_progress_good_max"
                    ],
                    VISION_TOLERANCE[
                        "ascent_progress_bad_min"
                    ]
                ),
                sync,
                "progress_delta",
                "GENERAL_STRENGTH",
                "Shoulder and hip progress during ascent."
            ),
            "head_control": self._item(
                self._lower_state(
                    head,
                    DETAIL_TOLERANCE[
                        "side_head_forward_good_max"
                    ],
                    DETAIL_TOLERANCE[
                        "side_head_forward_review_min"
                    ]
                ),
                head,
                "torso_length_ratio",
                "PHYSIQUE_CONTROL_LENS",
                "Secondary posture / presentation-control heuristic."
            ),
            "lockout_proxy": self._item(
                self._higher_state(
                    lockout,
                    DETAIL_TOLERANCE[
                        "side_lockout_good_min"
                    ],
                    DETAIL_TOLERANCE[
                        "side_lockout_review_below"
                    ]
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
                knee_angle,
                "deg",
                "ANGLE_DIAGNOSTIC",
                "Descriptive 2D angle; no universal squat cutoff."
            ),
            "hip_flexion_angle": self._item(
                "INFO",
                hip_angle,
                "deg",
                "ANGLE_DIAGNOSTIC",
                "Descriptive 2D angle; no universal squat cutoff."
            ),
            "trunk_lean_angle": self._item(
                "INFO",
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
                shin,
                "deg",
                "ANGLE_DIAGNOSTIC",
                "Shin inclination from vertical at deepest knee flexion."
            ),
        }

        general_keys = (
            "general_depth",
            "ascent_control",
            "head_control",
            "lockout_proxy",
        )

        detail_checks = {
            key: checks[
                key
            ]
            for key in general_keys
        }

        ipf_keys = (
            "ipf_depth_proxy",
            "lockout_proxy",
            "ascent_control",
        )

        ipf_checks = {
            key: checks[
                key
            ]
            for key in ipf_keys
        }

        detail_score = self._score_states(
            detail_checks
        )

        return {
            "checks": checks,
            "detail_score": detail_score,
            "detail_label": self._detail_label(
                detail_score
            ),
            "angle_metrics": {
                "min_knee_angle_deg": knee_angle,
                "min_hip_angle_deg": hip_angle,
                "max_trunk_lean_deg": trunk,
                "shin_angle_at_depth_deg": shin,
            },
            "competition_lenses": {
                "ipf_squat_proxy": {
                    "score": self._score_states(
                        ipf_checks
                    ),
                    "checks": {
                        key: checks[
                            key
                        ][
                            "state"
                        ]
                        for key in ipf_keys
                    },
                    "partial_proxy": True,
                    "official_referee_decision": False,
                },
                "physique_control": {
                    "score": self._score_states({
                        "head_control": checks[
                            "head_control"
                        ],
                    }),
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
                "detail_label": "INFO",
                "angle_metrics": {},
                "competition_lenses": {},
            }

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
