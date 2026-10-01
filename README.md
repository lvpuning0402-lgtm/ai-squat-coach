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
- Q or ESC — exit

## Tests

    python -m unittest discover -s tests

## Training history

    python history.py

Test-session history:

    python history.py --mode TEST --min-reps 1

Training feedback is not a medical diagnosis.
