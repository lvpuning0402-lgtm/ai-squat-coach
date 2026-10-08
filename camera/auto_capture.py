"""One hands-free screenshot per view after a steady, usable capture window."""
import math


class AutoCapture:
    def __init__(self, hold_seconds=3.0):
        self.hold_seconds = hold_seconds
        self.captured = set()
        self.reset_hold()

    def reset_hold(self):
        self.started = self.last_time = None
        self.view = None
        self.anchor = None

    def rearm(self):
        self.captured.clear()
        self.reset_hold()

    def update(self, now, view, raw_view, framing_status, landmarks):
        if view in self.captured:
            self.reset_hold()
            return False, 'AUTO PHOTO: saved for this view'
        if view not in ('FRONT', 'SIDE') or raw_view != view or framing_status != 'VISIBLE':
            self.reset_hold()
            return False, 'AUTO PHOTO: waiting for clear view'
        points = {}
        for index, item in landmarks.items():
            if not item or item.get('visibility', 0) < .60:
                continue
            point = item.get('point', ())
            if len(point) == 2 and all(math.isfinite(v) for v in point):
                points[index] = tuple(point)
        if not points:
            self.reset_hold()
            return False, 'AUTO PHOTO: waiting for keypoints'
        changed = (self.anchor is None or points.keys() != self.anchor.keys()
                   or any(math.dist(point, self.anchor[index]) > .025
                          for index, point in points.items()))
        interrupted = self.last_time is not None and not 0 <= now - self.last_time <= .5
        if changed or interrupted or self.view != view:
            self.started, self.view, self.anchor = now, view, points
        self.last_time = now
        remaining = self.hold_seconds - (now - self.started)
        if remaining > 0:
            return False, f'AUTO PHOTO: hold still {math.ceil(remaining)}s'
        self.captured.add(view)
        self.reset_hold()
        return True, 'AUTO PHOTO: capturing'
