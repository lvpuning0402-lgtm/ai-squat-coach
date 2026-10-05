"""Offline side-view phase boundaries from a synchronized per-rep trace.

This is an engineering window around peak landmark depth, not ground truth.
Live counting keeps its confirmation-based state machine.
"""
import math
from statistics import median


def align_side_frames(frames, truncated=False):
    audit = {'method': 'CENTERED_DEPTH_WINDOW_V1', 'status': 'UNAVAILABLE',
             'depth_band': .05, 'frame_count': len(frames)}
    if truncated or len(frames) < 5:
        audit['reason'] = 'TRACE_TRUNCATED' if truncated else 'TRACE_TOO_SHORT'
        return None, audit
    times = [f['time'] for f in frames]
    depths = [f['depth'] for f in frames]
    if not all(math.isfinite(v) for v in times + depths):
        audit['reason'] = 'TRACE_NONFINITE'
        return None, audit
    gaps = [b-a for a, b in zip(times, times[1:])]
    if any(g <= 0 or g > .25 for g in gaps):
        audit['reason'] = 'TRACE_TIME_GAP'
        return None, audit
    # Centered rather than causal smoothing avoids another time lag.
    signal = [median(depths[max(0, i-1):min(len(depths), i+2)])
              for i in range(len(depths))]
    peak = max(range(len(signal)), key=signal.__getitem__)
    lo = hi = peak
    threshold = signal[peak] - audit['depth_band']
    while lo > 0 and signal[lo-1] >= threshold:
        lo -= 1
    while hi+1 < len(signal) and signal[hi+1] >= threshold:
        hi += 1
    if lo == 0 or hi == len(frames)-1:
        audit['reason'] = 'TURNAROUND_NOT_BRACKETED'
        return None, audit
    groups = {'descent': frames[:lo], 'bottom': frames[lo:hi+1],
              'ascent': frames[hi+1:]}
    origin = times[0]
    audit.update(status='ALIGNED', confidence='MEDIUM',
                 peak_time_s=round(times[peak]-origin, 4),
                 bottom_start_s=round(times[lo]-origin, 4),
                 bottom_end_s=round(times[hi]-origin, 4),
                 phase_samples={k: len(v) for k, v in groups.items()})
    return groups, audit
