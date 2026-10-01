# Squat Standard Profile

AI-Sport-Coach does not use one user's calibration values as movement-quality standards.

## Default profile: GENERAL_STRENGTH

The default profile follows published strength-and-conditioning guidance rather than competition-only rules.

NSCA guidance used by the project emphasizes:

- descend until the thighs are close to parallel with the floor;
- keep the knees tracking over the feet/toes;
- maintain controlled trunk/head position;
- during the upward phase, the hips, knees and shoulders return to upright together.

ACE coaching guidance is used as a secondary cross-check for:

- knees remaining aligned over the second toe;
- thighs reaching parallel or almost parallel;
- hips and torso rising together.

## Competition-depth reference

The project also stores an **IPF depth proxy**.

The current IPF Technical Rulebook (effective 1 March 2026) requires the top surface of the legs at the hip joint to be lower than the top of the knees.

A webcam cannot reproduce an official referee decision because MediaPipe estimates landmark centers rather than the anatomical surfaces named in the rule.

Therefore:

- GENERAL_STRENGTH depth uses a small 2D landmark tolerance around parallel;
- IPF depth proxy requires the hip landmark to reach or pass the knee-landmark level;
- neither is labeled an official competition decision.

## Three different kinds of values

The software keeps these separate:

1. **Movement standards** — externally sourced coaching or competition rules.
2. **Vision tolerances** — engineering allowances for a 2D webcam.
3. **Diagnostic metrics** — useful measurements without one universal pass/fail cutoff.

Examples:

- Knee tracking is a movement standard; the numeric amount of landmark drift allowed by the webcam is an engineering tolerance.
- Torso lean is diagnostic. There is no single universal torso angle that is correct for every squat style, body proportion, stance or bar position.
- Front-view symmetry is diagnostic rather than a universal squat rule.

## Current standardized checks

### SIDE_GENERAL_STRENGTH

- **Depth**: approximately parallel or below using a hip-to-knee landmark proxy.
- **Ascent control**: shoulder and hip progress are compared only during the ascent phase.

The software also records:

- **IPF depth proxy**: stricter landmark-level depth reference.
- trunk lean, head position, knee angle and hip angle as diagnostic information.

### FRONT_TECHNIQUE_ONLY

- **Knee tracking**: knees should remain aligned over the feet/toes.
- **Ascent control**: shoulder and hip progress are compared during ascent.

The front camera view does **not** certify squat depth. A front-view PASS means only that the checks visible from that view passed.

## References

- National Strength and Conditioning Association (NSCA), TSAC Report squat technique guidance: knees track over toes, thighs close to parallel, hips/knees/shoulders return together.
- American Council on Exercise (ACE), Bodyweight Squat exercise guidance: thighs parallel or almost parallel, knees aligned over the second toe, hips and torso rise together.
- International Powerlifting Federation (IPF), Technical Rulebook effective 1 March 2026, squat depth rule.

Training feedback is not a medical diagnosis.
