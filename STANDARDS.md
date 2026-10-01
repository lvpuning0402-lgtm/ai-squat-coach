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

## Multi-competition detail lens

The primary squat pass/fail profile remains **GENERAL_STRENGTH**. A second,
non-official detail layer is now used to give more granular feedback.

This layer deliberately separates three lenses:

### 1. GENERAL_STRENGTH

The hard movement standard already used by the project:

- knee tracking in the front view;
- approximately parallel-or-below depth in the side view;
- shoulder/hip coordination during ascent.

### 2. IPF_SQUAT_PROXY

The 2026 IPF Technical Rulebook requires, among other things:

- the lifter to start and finish upright with the knees locked;
- the hip crease / top surface of the leg at the hip joint to descend below
  the top of the knee;
- no double bounce or downward movement during the ascent;
- no stepping forward, backward or laterally during the attempt.

A single webcam cannot reproduce an official referee decision. The project
therefore labels measurable items as **proxies**. At present it reports:

- IPF depth landmark proxy;
- return-to-upright / knee-extension proxy;
- ascent-control proxy.

These are not official white/red-light decisions.

### 3. PHYSIQUE_CONTROL_LENS

IFBB Pro / NPC Worldwide physique divisions do not publish squat-technique
standards. Their judging criteria repeatedly emphasize visual qualities such as
**symmetry, balance, shape and presentation** (with muscularity/condition also
used depending on the division).

The project borrows only the movement-control concepts that a pose camera can
reasonably observe:

- shoulder level;
- hip/pelvis level;
- left-right knee-angle symmetry;
- knee-height symmetry;
- lateral center balance;
- head/posture control.

It does **not** claim that these are official IFBB/NPC squat scores, and it does
not attempt to score muscle size, leanness, conditioning or bodybuilding
placement from a squat video.

## Detail states

Secondary detail checks use three states:

- **PASS** — within the conservative webcam tolerance;
- **WATCH** — a visible deviation worth monitoring;
- **REVIEW** — a larger deviation that the coach should call out.

These states do not automatically change the hard GENERAL_STRENGTH pass/fail
result. They exist so a technically valid squat can still receive useful
coaching detail instead of simply being labeled "no problem".

Current FRONT detail measurements include:

- knee tracking;
- ascent coordination;
- shoulder level;
- hip level;
- lateral center shift;
- head control;
- left/right knee-angle symmetry;
- knee-height symmetry.

Current SIDE detail measurements include:

- GENERAL_STRENGTH depth;
- IPF depth proxy;
- ascent coordination;
- return-to-upright / lockout proxy;
- head-position control;
- knee flexion angle;
- hip flexion angle;
- trunk lean angle;
- shin angle at deepest knee flexion.

Absolute torso, hip, knee and shin angles are retained as **diagnostic angle
measurements** where no single universal competition cutoff exists.

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
- International Powerlifting Federation (IPF), Technical Rulebook effective 1 March 2026, squat performance rules.
- IFBB Professional League / NPC Worldwide competition rules, physique judging concepts including symmetry, balance, muscularity and presentation. The project uses only symmetry/balance/presentation-inspired movement-control concepts, not physique-placement scoring.

Training feedback is not a medical diagnosis.
