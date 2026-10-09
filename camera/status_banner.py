"""Camera text that adapts to the brightness directly behind it."""
from collections import OrderedDict
from math import exp
from time import monotonic

import cv2


class AdaptiveTextColors:
    """Time-based smoothing, hysteresis and dwell per screen position."""

    def __init__(self):
        self.states = OrderedDict()

    def clear(self):
        self.states.clear()

    def color(self, key, brightness, now):
        state = self.states.pop(key, None)
        if state is None or now - state['seen'] > 2 or now < state['seen']:
            state = dict(mean=brightness, dark=brightness >= 145,
                         seen=now, changed=now, pending=None)
        else:
            dt = now - state['seen']
            state['mean'] += (brightness - state['mean']) * (1 - exp(-dt / .3))
            state['seen'] = now
            # A neutral band preserves the current color under exposure noise.
            change = (state['mean'] < 120 if state['dark']
                      else state['mean'] > 170)
            if not change:
                state['pending'] = None
            elif state['pending'] is None:
                state['pending'] = now
            elif now - state['pending'] >= .7 and now - state['changed'] >= 1.5:
                state['dark'] = not state['dark']
                state['changed'] = now
                state['pending'] = None
        self.states[key] = state
        if len(self.states) > 128:
            self.states.popitem(last=False)
        return (0, 0, 0) if state['dark'] else (255, 255, 255)


_live_colors = AdaptiveTextColors()


def reset_text_colors():
    _live_colors.clear()


def text_color(frame, text, x, y, scale, thickness=1):
    """Sample the visible text area before drawing; return one foreground color."""
    (width, height), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    rows, cols = frame.shape[:2]
    left, right = max(0, x), min(cols, x + width + 1)
    top, bottom = max(0, y - height), min(rows, y + baseline + 1)
    brightness = 0
    if left < right and top < bottom:
        region = frame[top:bottom, left:right]
        brightness = cv2.mean(cv2.cvtColor(region, cv2.COLOR_BGR2GRAY))[0]
    # Content and font size can change during the countdown; keep its history.
    return _live_colors.color((rows, cols, x, y), brightness, monotonic())


def draw_adaptive_text(frame, text, x, y, scale=.47, thickness=1):
    text = str(text)
    if not text:
        return
    ink = text_color(frame, text, x, y, scale, thickness)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, ink, thickness, cv2.LINE_AA)


def draw_status_banner(frame, message, bottom=34):
    height, width = frame.shape[:2]
    message = str(message)
    scale = .52
    (text_width, _), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    if text_width > max(1, width - 32):
        scale *= max(1, width - 32) / text_width
    (_, text_height), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    y = max(text_height + 16, height - bottom)
    draw_adaptive_text(frame, message, 16, y, scale=scale)
