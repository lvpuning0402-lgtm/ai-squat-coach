"""Per-view, per-phase observations; never a replacement for matched comparisons."""
import math
from collections import Counter
from statistics import mean

PHASES = ('descent', 'bottom', 'ascent')


def summarize_phase_observations(reps):
    result = {}
    for view in ('FRONT', 'SIDE'):
        candidates = [r for r in reps if r.get('view') == view
                      and r.get('analysis_valid', True) and r.get('set_valid', True)]
        if not candidates:
            continue
        phases = {}
        for phase in PHASES:
            accepted = []
            excluded = Counter()
            for rep in candidates:
                data = rep.get('phase_scores', {}).get(phase, {})
                evidence = rep.get('confidence_breakdown', {})
                score = data.get('score')
                if any(evidence.get(k) not in ('HIGH', 'MEDIUM')
                       for k in ('pose_quality', 'view_quality')):
                    excluded['CAPTURE_UNUSABLE'] += 1
                elif not isinstance(score, (int, float)) or not math.isfinite(score):
                    excluded['SCORE_UNAVAILABLE'] += 1
                elif data.get('confidence') not in ('HIGH', 'MEDIUM') or data.get('samples', 0) < 2:
                    excluded['PHASE_EVIDENCE_LIMITED'] += 1
                else:
                    accepted.append((rep, data))
            phases[phase] = {
                'score': round(mean(d['score'] for _, d in accepted), 1) if accepted else None,
                'confidence': ('MEDIUM' if any(d['confidence'] == 'MEDIUM' for _, d in accepted)
                               else 'HIGH') if accepted else 'LOW',
                'evaluated_reps': len(accepted), 'eligible_reps': len(candidates),
                'excluded_reps': len(candidates)-len(accepted),
                'rep_ids': [r.get('rep') for r, _ in accepted],
                'exclusion_reasons': dict(excluded),
            }
        result[view] = phases
    return result
