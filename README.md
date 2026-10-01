# AI-Sport-Coach

A local AI-powered sports movement analysis system based on computer vision.

## Current squat standard

The default evaluation profile is:

**GENERAL_STRENGTH**

It is aligned to published strength-and-conditioning guidance rather than to one user's personal calibration data.

Core rules:

- squat to approximately parallel or below;
- knees track over the feet/toes;
- maintain neutral body control;
- hips and shoulders return together during ascent.

Competition depth is referenced to the IPF rule, but webcam landmarks are only an approximation and are not an official referee decision.

See STANDARDS.md for the distinction between:

- external movement standards;
- 2D camera engineering tolerances;
- diagnostic metrics that do not have one universal numeric cutoff.

## Run

    python -m camera.camera

Controls:

- M — switch SIMPLE / DETAIL / DEBUG
- T — switch TEST / TRAINING before the first completed rep
- Q or ESC — finish the set and open the visual session summary
- Q / ESC / Enter on the summary screen — close

## Tests

    python -m unittest discover -s tests

## AI Coach feedback

Completed sets now include a deterministic coaching summary:

- what went well;
- the main technique issue to focus on;
- one concrete cue for the next set;
- a separate formal progress summary for TRAINING sessions.

The coach layer only explains metrics already measured by the pose system. It does not make medical diagnoses, and TEST sessions do not generate formal training-trend conclusions.

Session JSON reports include a `coach_feedback` object. Formal history JSON reports include `progress_feedback`.

The movement report now also includes a secondary `MULTI_COMPETITION_DETAIL` layer.

The detail layer now uses weighted continuous scoring rather than equal fixed
scores. FRONT prioritizes knee tracking and ascent control; SIDE prioritizes
depth and ascent control. Separate IPF proxy and physique-control scores use
their own weights. The exact project weights and score bands are documented in
`STANDARDS.md`.

Each completed squat is also split into **descent / bottom / ascent** scores.
The report stores the phase-specific checks and identifies the weakest phase,
so feedback can say whether the main loss of control happened on the way down,
at the bottom, or during the ascent.

It keeps the hard squat standard separate from additional coaching detail:

- FRONT: shoulder level, hip level, center balance, head control, left/right knee-angle symmetry and knee-height symmetry;
- SIDE: GENERAL depth, IPF depth proxy, ascent control, return-to-upright proxy, head control, knee/hip/trunk/shin angles;
- IFBB/NPC physique judging concepts are used only as a symmetry/balance/presentation-inspired visual-control lens;
- bodybuilding muscularity/conditioning is not scored from squat video, and the physique lens is not an official bodybuilding or squat judging score.

When a set is ended with Q / ESC, the camera window now switches to a visual session summary with:

- valid reps, score and standard pass rate;
- GENERAL depth / IPF proxy rates when SIDE reps are present;
- the main AI Coach focus and next cue;
- a per-rep timeline showing PASS / REVIEW / EXCLUDED, score and issue.

## Training history

    python history.py

Test-session history:

    python history.py --mode TEST --min-reps 1

Training feedback is not a medical diagnosis.
