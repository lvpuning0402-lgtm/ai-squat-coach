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
