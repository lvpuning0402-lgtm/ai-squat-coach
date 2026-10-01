"""
Squat movement standards used by AI-Sport-Coach.

Important distinction:
- Movement standards come from published coaching / competition rules.
- Numeric camera tolerances are engineering tolerances for 2D pose estimation.
  They are NOT claimed to be universal human biomechanical cutoffs.

Default product profile:
GENERAL_STRENGTH

Primary references:
- NSCA strength-and-conditioning squat guidance:
  thighs approximately parallel, knees tracking over the feet/toes,
  neutral spine/head, and hips/shoulders returning together.
- IPF technical rules:
  competition depth requires the top surface of the legs at the hip joint
  to be lower than the top of the knees.

Because MediaPipe provides landmark centers rather than anatomical surfaces,
the project reports "landmark depth" and does not claim to make an official
IPF referee decision.
"""


STANDARD_NAME = "GENERAL_STRENGTH"
STANDARD_VERSION = "2026.10"

STANDARD_RULES = {
    "depth": "PARALLEL_OR_BELOW",
    "knee_tracking": "KNEES_OVER_FEET",
    "spine": "NEUTRAL",
    "head": "NEUTRAL",
    "ascent": "HIPS_AND_SHOULDERS_TOGETHER",
}

SOURCE_LABELS = {
    "general_strength": "NSCA",
    "competition_depth": "IPF",
}

# 2D vision tolerances.
# These are normalized to body dimensions and are intentionally separated
# from the movement standards above.
VISION_TOLERANCE = {
    # Positive front inward value means the knee is farther toward the
    # midline than the ankle. 0.10 = 10% of hip width.
    "knee_in_good_max": 0.10,
    "knee_in_bad_min": 0.20,

    # Knee-height asymmetry is diagnostic only, not a universal squat rule.
    "symmetry_good_max": 0.15,
    "symmetry_bad_min": 0.30,

    # Shoulder / hip vertical desynchronization.
    # General-strength depth uses a small landmark tolerance because
    # MediaPipe estimates joint centers while coaching guidance describes
    # the thigh relative to the floor. -0.05 = hip landmark may remain up
    # to 5% of thigh length above the knee landmark and still count as
    # approximately parallel. IPF proxy remains strict at >= 0.0.
    "general_depth_margin_min": -0.05,
    "ipf_depth_margin_min": 0.0,

    # Ascent coordination is measured as the difference between shoulder
    # and hip progress fractions from bottom to standing. These are camera
    # engineering tolerances, not anatomical cutoffs.
    "ascent_progress_good_max": 0.15,
    "ascent_progress_bad_min": 0.30,

    # Camera-position / tracking outlier limits.
    "front_center_outlier": 1.25,
    "front_sync_outlier": 0.80,
    "side_sync_outlier": 1.50,
}

# Internal state-machine thresholds.
# These are detection thresholds, not exercise-quality standards.
DETECTION = {
    "side_start_knee_angle": 155.0,
    "side_bottom_knee_angle": 120.0,
    "side_standing_knee_angle": 155.0,
    "side_standing_like_angle": 165.0,
}
