"""Advisory framing checks; never gate rep counting or alter scores."""
import math

GROUPS = ((0, 'HEAD'), (11, 'SHOULDERS'), (12, 'SHOULDERS'),
          (23, 'HIPS'), (24, 'HIPS'), (25, 'KNEES'), (26, 'KNEES'),
          (27, 'ANKLES'), (28, 'ANKLES'))


def framing_hint(landmarks, view, active_leg=None, detected=True):
    """Check measured points, not a guarantee of full-body or squat clearance."""
    if not detected:
        return {'status': 'NO_POSE', 'message': 'CAPTURE: body not detected'}
    groups = GROUPS
    if view == 'SIDE' and active_leg in ('LEFT', 'RIGHT'):
        indices = {0, 11, 23, 25, 27} if active_leg == 'LEFT' else {0, 12, 24, 26, 28}
        groups = tuple(g for g in GROUPS if g[0] in indices)
    outside, unclear, edge = [], [], []
    for index, name in groups:
        item = landmarks.get(index) or {}
        point = item.get('point', ())
        visibility = item.get('visibility', 0)
        if (not isinstance(point, (tuple, list)) or len(point) != 2
                or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in point)):
            unclear.append(name)
            continue
        if any(v < 0 or v > 1 for v in point):
            outside.append(name)
        elif (not isinstance(visibility, (int, float)) or not math.isfinite(visibility)
              or visibility < .60):
            unclear.append(name)
        elif any(v < .04 or v > .96 for v in point):
            edge.append(name)
    for names, status, suffix in ((outside, 'OUT_OF_FRAME', 'out of frame'),
                                  (unclear, 'LOW_VISIBILITY', 'not clear'),
                                  (edge, 'NEAR_EDGE', 'near edge')):
        if names:
            return {'status': status, 'message': f'{names[0]}: {suffix}'}
    return {'status': 'VISIBLE', 'message': 'CAPTURE: keypoints visible'}
