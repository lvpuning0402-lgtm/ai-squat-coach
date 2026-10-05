import unittest
from unittest.mock import patch

from exercises.phase_alignment import align_side_frames
from exercises.side_squat import SideSquatAnalyzer
from feedback.competition_detail import CompetitionDetailEvaluator


def trace(depths, dt=.05):
    return [dict(time=i*dt, depth=d, knee_angle=140-100*d, hip_angle=100-80*d,
                 trunk=20+10*d, shin=20, head=.12, sync=.03,
                 shoulder=.4+.2*d, hip=.4+.2*d) for i, d in enumerate(depths)]


class SideAlignmentTests(unittest.TestCase):
    def test_no_pause_turnaround_partitions_each_frame_once(self):
        frames = trace([-.8, -.5, -.2, .10, .20, .10, -.2, -.5, -.8])
        groups, audit = align_side_frames(frames)
        self.assertEqual(audit['status'], 'ALIGNED')
        self.assertEqual([f for group in groups.values() for f in group], frames)
        self.assertEqual(max(f['depth'] for f in groups['bottom']), .2)
        self.assertEqual(audit['phase_samples']['bottom'], 3)

    def test_pause_preserves_real_plateau_samples(self):
        frames = trace([-.8, -.5, -.2] + [.2]*8 + [-.2, -.5, -.8])
        groups, _ = align_side_frames(frames)
        self.assertEqual(len(groups['bottom']), 8)

    def test_fast_low_frame_rate_does_not_duplicate_samples(self):
        groups, _ = align_side_frames(trace([-.8, -.3, .1, .2, .1, -.3, -.8], .15))
        self.assertEqual(sum(map(len, groups.values())), 7)

    def test_time_gap_truncation_and_unbracketed_are_unavailable(self):
        for frames, truncated, reason in (
            (trace([-.8, -.3, .2, .2, -.3, -.8], .3), False, 'TRACE_TIME_GAP'),
            (trace([-.8, -.3, .2, .2, -.3, -.8]), True, 'TRACE_TRUNCATED'),
            (trace([-.8, -.6, -.4, -.2, 0, .2]), False, 'TURNAROUND_NOT_BRACKETED'),
        ):
            groups, audit = align_side_frames(frames, truncated)
            self.assertIsNone(groups)
            self.assertEqual(audit['reason'], reason)

    def test_single_peak_spike_not_promoted_to_credible_bottom(self):
        a = SideSquatAnalyzer()
        a.phase_trace = trace([-.8, -.6, -.4, -.2, .8, -.2, -.4, -.6, -.8])
        a.current_max_depth_margin = .8
        rep = a.complete_rep(1)
        result = CompetitionDetailEvaluator().evaluate(rep)
        # Centered median resists the spike; remaining peak-vs-phase conflict
        # or sparse phase evidence cannot authorize reliable coaching.
        self.assertNotEqual(result['detail_confidence'], 'HIGH')
        self.assertIsNone(result['weakest_phase'])

    def test_completed_rep_uses_same_frame_angles_and_depth(self):
        a = SideSquatAnalyzer()
        a.phase_trace = trace([-.8, -.5, -.2, .10, .20, .10, -.2, -.5, -.8])
        # Reproduce delayed online BOTTOM containing already-rising samples.
        a._record_phase_metrics('BOTTOM', 120, 100, 30, 20, .12, .03, None, -.2)
        a.current_max_depth_margin = .2
        rep = a.complete_rep(1)
        bottom = rep['phase_metrics']['bottom']
        self.assertEqual(bottom['max_depth_margin'], .2)
        self.assertEqual(bottom['min_knee_angle'], 120)
        self.assertEqual(bottom['samples'], 3)
        self.assertEqual(rep['phase_alignment']['status'], 'ALIGNED')
        self.assertEqual(len(rep['phase_trace']), 9)
        self.assertEqual(a.phase_trace, [])
        self.assertEqual(sum(v['samples'] for v in rep['phase_metrics'].values()), 9)
        result = CompetitionDetailEvaluator().evaluate(rep)
        self.assertNotIn('BOTTOM_DEPTH_PHASE_MISMATCH', result['confidence_breakdown']['reasons'])
        self.assertEqual(result['phase_scores']['bottom']['confidence'], 'MEDIUM')

    def test_full_no_pause_cycle_counts_once_and_exports_aligned_bottom(self):
        a = SideSquatAnalyzer()
        sequence = ([0]*15 + [i/20 for i in range(1, 21)]
                    + [i/20 for i in range(19, -1, -1)] + [0]*20)
        completed = []
        for i, depth in enumerate(sequence):
            with patch('exercises.side_squat.calculate_angle',
                       side_effect=[175-110*depth, 175-110*depth]), patch(
                           'exercises.side_squat.time.perf_counter', return_value=i*.05):
                result = a.analyze(
                    (.4-.1*depth, .08+.25*depth), (.4-.1*depth, .15+.25*depth),
                    (.4, .45+.25*depth), (.6, .65), (.6, .95))
            if result.get('rep_completed'):
                completed.append(result['rep_summary'])
        self.assertEqual(len(completed), 1)
        rep = completed[0]
        self.assertEqual(rep['phase_alignment']['status'], 'ALIGNED')
        self.assertAlmostEqual(rep['phase_metrics']['bottom']['max_depth_margin'],
                               rep['max_depth_margin'])
        groups, audit = align_side_frames(rep['phase_trace'])
        self.assertEqual(audit['phase_samples'], rep['phase_alignment']['phase_samples'])
        self.assertEqual(sum(len(v) for v in groups.values()), len(rep['phase_trace']))

    def test_trace_reset_and_limit(self):
        a = SideSquatAnalyzer()
        frame = trace([.1])[0]
        for _ in range(1802):
            a._append_phase_frame(frame)
        self.assertEqual(len(a.phase_trace), 1800)
        self.assertTrue(a.phase_trace_truncated)
        a.reset_rep_metrics()
        self.assertEqual(a.phase_trace, [])
        self.assertFalse(a.phase_trace_truncated)

    def test_live_analyzer_records_raw_angles_not_causal_medians(self):
        a = SideSquatAnalyzer()
        a.phase = 'DESCENDING'
        a.baseline_shoulder_y = .2
        a.baseline_hip_y = .5
        a.baseline_torso_length = .3
        a.knee_buffer.extend([140]*7)
        with patch('exercises.side_squat.calculate_angle', side_effect=[80, 65]):
            a.analyze((.2,.25), (.3,.4), (.4,.7), (.6,.65), (.6,.95))
        self.assertEqual(a.phase_trace[-1]['knee_angle'], 80)
        self.assertEqual(a.phase_trace[-1]['hip_angle'], 65)


if __name__ == '__main__':
    unittest.main()
