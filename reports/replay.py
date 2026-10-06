"""Re-evaluate a saved report without camera access or database writes.

python -m reports.replay reports/session_35_20261006_004717.json
python -m reports.replay INPUT.json --output reports/replay_result.json
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from exercises.front_squat import FrontSquatAnalyzer
from exercises.side_squat import SideSquatAnalyzer
from feedback.performance import SessionPerformanceAnalyzer
from feedback.insights import SessionInsightBuilder


def replay_report(source):
    if not isinstance(source, dict) or not isinstance(source.get('reps'), list):
        raise ValueError('Expected a session report with a reps list.')
    analyzer = SessionPerformanceAnalyzer()
    results, replay_notes = [], []
    fields = {
        'SIDE': {'time', 'depth', 'knee_angle', 'hip_angle', 'trunk', 'shin',
                 'head', 'sync', 'shoulder', 'hip'},
        'FRONT': {'time', 'displacement', 'head', 'shoulder_tilt', 'hip_tilt',
                  'center', 'knee_asymmetry', 'knee_angle', 'sync', 'shoulder',
                  'hip', 'left_inward', 'right_inward', 'knee_height'},
    }
    for original in source['reps']:
        if not isinstance(original, dict) or original.get('view') not in fields:
            raise ValueError('Each rep must specify FRONT or SIDE.')
        rep = deepcopy(original)
        frames = rep.get('phase_trace')
        status = 'LEGACY_AGGREGATES_ONLY'
        if frames:
            required = fields[rep['view']]
            if not isinstance(frames, list) or len(frames) > 1800:
                raise ValueError('Invalid or oversized phase trace.')
            for frame in frames:
                if (not isinstance(frame, dict) or not required <= frame.keys()
                    or any(not isinstance(frame[k], (int, float)) or not math.isfinite(frame[k])
                           for k in required)):
                    raise ValueError('Phase trace has missing or nonfinite measurements.')
            engine = SideSquatAnalyzer() if rep['view'] == 'SIDE' else FrontSquatAnalyzer()
            engine.phase_trace = frames
            engine.phase_trace_truncated = rep.get('phase_alignment', {}).get('reason') == 'TRACE_TRUNCATED'
            audit = engine._aligned_phase_metrics()
            rep['phase_alignment'] = audit
            if audit['status'] == 'ALIGNED':
                rep['phase_metrics'] = engine.phase_metrics
            status = audit['status']
        results.append(analyzer.analyze_rep(rep))
        replay_notes.append({'rep': rep.get('rep'), 'status': status})
    summary = analyzer.get_set_summary()
    return {'report_version': 3, 'report_context': 'OFFLINE_REPLAY',
            'session_type': source.get('session_type', 'TEST'),
            'source_session_id': source.get('session_id'),
            'source_report_version': source.get('report_version'),
            'database_written': False, 'replay_notes': replay_notes,
            'summary': summary,
            'coach_feedback': SessionInsightBuilder().build(results, summary,
                                                            source.get('session_type', 'TEST')),
            'reps': results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, help='New JSON path; existing files are never overwritten.')
    args = parser.parse_args(argv)
    try:
        raw = args.input.read_bytes()
        report = replay_report(json.loads(raw))
        report['source_sha256'] = hashlib.sha256(raw).hexdigest()
        if args.output:
            # Exclusive creation protects both originals and previous replay outputs.
            encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(encoded)
        print(json.dumps({'source_session_id': report['source_session_id'],
                          'reps': len(report['reps']), 'replay_notes': report['replay_notes'],
                          'phase_observations_by_view': report['summary'].get('phase_observations_by_view', {}),
                          'coach_focus': report['coach_feedback'].get('selected_focus'),
                          'database_written': False}, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f'Replay failed: {exc}\n')


if __name__ == '__main__':
    main()
