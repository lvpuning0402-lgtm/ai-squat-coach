"""
Competition-informed secondary detail profiles.

Important:
- Bodybuilding / physique contests do not publish a squat-technique rulebook.
- IFBB Pro / NPC Worldwide judging concepts such as symmetry, balance and
  presentation are used only as a secondary visual-control lens.
- IPF squat rules are used only for measurable squat-performance proxies.
- Numeric thresholds below are 2D webcam engineering heuristics, not official
  contest judging cutoffs and not medical criteria.
"""

DETAIL_PROFILE_NAME = "MULTI_COMPETITION_DETAIL"
DETAIL_PROFILE_VERSION = "2026.10"

COMPETITION_LENSES = {
    "GENERAL_STRENGTH": {
        "purpose": "dynamic squat technique",
        "source": "NSCA/ACE-style coaching principles",
    },
    "IPF_SQUAT_PROXY": {
        "purpose": "competition squat execution proxy",
        "source": "IPF Technical Rulebook 2026",
        "measurable_now": [
            "depth",
            "upright_return_proxy",
            "ascent_control_proxy",
        ],
        "not_official": True,
    },
    "PHYSIQUE_CONTROL_LENS": {
        "purpose": (
            "movement symmetry, balance and presentation control"
        ),
        "source": "IFBB Pro / NPC Worldwide judging concepts",
        "not_official_squat_standard": True,
    },
}

# Secondary detail tolerances.
# These values deliberately do NOT affect the hard GENERAL_STRENGTH pass/fail
# unless the same metric is already part of the primary standard.
DETAIL_TOLERANCE = {
    # FRONT normalized to visible body width.
    "head_shift_good_max": 0.08,
    "head_shift_review_min": 0.18,

    "shoulder_tilt_good_max": 0.08,
    "shoulder_tilt_review_min": 0.16,

    "hip_tilt_good_max": 0.08,
    "hip_tilt_review_min": 0.16,

    "center_shift_good_max": 0.08,
    "center_shift_review_min": 0.18,

    # Difference between left/right 2D knee flexion angles.
    "knee_angle_asym_good_max": 10.0,
    "knee_angle_asym_review_min": 20.0,

    # Existing knee-height symmetry ratio.
    "front_symmetry_good_max": 0.15,
    "front_symmetry_review_min": 0.30,

    # SIDE head displacement normalized to torso length.
    "side_head_forward_good_max": 0.20,
    "side_head_forward_review_min": 0.35,

    # Return-to-upright proxies. These are not official IPF lockout calls.
    "side_lockout_good_min": 165.0,
    "side_lockout_review_below": 155.0,
}

DETAIL_STATE_SCORE = {
    "PASS": 100.0,
    "WATCH": 82.0,
    "REVIEW": 62.0,
    "INFO": None,
}

# Weighted scoring profiles.
# These weights are project design choices for coaching emphasis. They are NOT
# official federation score sheets. Each profile sums to 1.0.
DETAIL_WEIGHTS = {
    "FRONT_COACH": {
        "knee_tracking": 0.24,
        "ascent_control": 0.18,
        "center_balance": 0.14,
        "hip_level": 0.12,
        "knee_angle_symmetry": 0.12,
        "shoulder_level": 0.08,
        "head_control": 0.06,
        "knee_height_symmetry": 0.06,
    },
    "SIDE_COACH": {
        "general_depth": 0.35,
        "ascent_control": 0.30,
        "lockout_proxy": 0.20,
        "head_control": 0.15,
    },
    "IPF_SQUAT_PROXY": {
        "ipf_depth_proxy": 0.45,
        "ascent_control": 0.30,
        "lockout_proxy": 0.25,
    },
    "PHYSIQUE_CONTROL_FRONT": {
        "shoulder_level": 0.20,
        "hip_level": 0.22,
        "center_balance": 0.20,
        "knee_angle_symmetry": 0.16,
        "knee_height_symmetry": 0.12,
        "head_control": 0.10,
    },
}

# Continuous-score anchors used inside the PASS/WATCH/REVIEW bands.
# PASS remains 90-100, WATCH 70-<90, REVIEW below 70.
CONTINUOUS_SCORING = {
    "pass_floor": 90.0,
    "watch_floor": 70.0,
    "review_floor": 40.0,
    "extreme_multiplier": 2.0,
}

DETAIL_GRADE_BANDS = [
    (95.0, "A+"),
    (90.0, "A"),
    (85.0, "B+"),
    (80.0, "B"),
    (75.0, "C+"),
    (70.0, "C"),
    (60.0, "D"),
    (0.0, "E"),
]

