# Squat Standard Profile

AI-Sport-Coach no longer treats one user's calibration values as movement-quality standards.

## Default profile: GENERAL_STRENGTH

The default squat standard is aligned to published NSCA coaching guidance:

- descend to approximately parallel or below while technique is maintained;
- knees track over the feet/toes;
- maintain a neutral spine and head position;
- hips, knees, and shoulders return together during ascent.

For competition-style depth, the project also references the IPF rule that the top surface of the legs at the hip joint must be lower than the top of the knees.

## What the camera can and cannot standardize

MediaPipe estimates landmark centers. It does not directly measure:

- the top surface of the thigh;
- lumbar vertebral alignment;
- exact foot pressure;
- bar path;
- joint moments or forces.

Therefore the software distinguishes:

1. **movement standards** — externally sourced rules;
2. **vision tolerances** — engineering allowances for a 2D webcam;
3. **diagnostic metrics** — useful measurements that are not universal pass/fail standards.

For example, torso lean is no longer judged with one universal angle. Squat style, bar position, limb lengths and mobility change the amount of forward lean that is normal.

## Current standardized pass/fail items

### SIDE
- Landmark depth: hip landmark reaches the level of or below the knee landmark.
- Ascent control: shoulder/hip movement synchronization is monitored.

### FRONT
- Knee tracking: knee should remain aligned over the foot.
- Left/right symmetry remains a diagnostic metric, not a universal rule.

## References

- National Strength and Conditioning Association (NSCA), squat technique guidance and Basics of Strength and Conditioning.
- International Powerlifting Federation (IPF), Technical Rules Book, squat depth rule.

This project provides training feedback and is not a medical diagnostic system.
