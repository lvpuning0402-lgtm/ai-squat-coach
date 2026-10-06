import unittest
from unittest.mock import patch

from exercises.front_squat import FrontSquatAnalyzer
from exercises.phase_alignment import align_front_frames
from feedback.front_feedback import merge_front_rep_feedback
from feedback.competition_detail import CompetitionDetailEvaluator
import test_front_squat as fixtures


class FrontAlignmentTests(unittest.TestCase):
    def run_cycle(self, pause=0, knee_inward=False):
        analyzer = FrontSquatAnalyzer()
        sequence = ([0]*12 + [.22*i/18 for i in range(1, 19)]
                    + [.22]*pause + [.22*i/18 for i in range(17, -1, -1)] + [0]*18)
        completed = []
        for i, d in enumerate(sequence):
            with patch('exercises.front_squat.time.perf_counter', return_value=i*.04):
                result = fixtures.FrontSquatAnalyzerTests.feed(
                    analyzer, fixtures.FrontSquatAnalyzerTests.frame(d, knee_inward))
            if result.get('rep_completed'):
                completed.append(result['rep_summary'])
        self.assertEqual(len(completed), 1)
        self.assertEqual(analyzer.phase_trace, [])
        return completed[0]

    def test_no_pause_and_pause_have_disjoint_actual_frames(self):
        for pause in (0, 8):
            rep = self.run_cycle(pause)
            self.assertEqual(rep['phase_alignment']['status'], 'ALIGNED')
            groups, audit = align_front_frames(rep['phase_trace'])
            self.assertEqual(audit['phase_samples'], rep['phase_alignment']['phase_samples'])
            self.assertEqual(sum(x['samples'] for x in rep['phase_metrics'].values()), len(rep['phase_trace']))
            self.assertEqual(max(f['displacement'] for f in groups['bottom']),
                             max(f['displacement'] for f in rep['phase_trace']))
            self.assertIn('max_left_inward', rep['phase_metrics']['bottom'])

    def test_inward_geometry_still_counts_without_sharing_delayed_metrics(self):
        rep = self.run_cycle(knee_inward=True)
        bottom = rep['phase_metrics']['bottom']
        self.assertGreater(bottom['max_left_inward'], 0)
        feedback = {'max_left_inward': .7, 'phase_metrics': {
            'bottom': {'samples': 99, 'max_left_inward': .99}}}
        merged = merge_front_rep_feedback(rep, feedback)
        self.assertEqual(merged['phase_metrics'], rep['phase_metrics'])
        self.assertEqual(merged['max_left_inward'], .7)
        self.assertIn('phase_metrics', feedback)  # inputs are not mutated

    def test_unaligned_legacy_phase_merge_remains_available(self):
        rep = {'phase_metrics': {'bottom': {'samples': 3}}}
        merged = merge_front_rep_feedback(rep, {'phase_metrics': {
            'bottom': {'samples': 2, 'max_left_inward': .1}}})
        self.assertEqual(merged['phase_metrics']['bottom'], {'samples': 3, 'max_left_inward': .1})
        self.assertNotIn('max_left_inward', rep['phase_metrics']['bottom'])

    def test_alignment_cannot_claim_high_confidence(self):
        rep = self.run_cycle(pause=8)
        rep['capture_quality'] = {'pose_quality': 'HIGH', 'view_quality': 'HIGH'}
        result = CompetitionDetailEvaluator().evaluate(rep)
        self.assertNotEqual(result['detail_confidence'], 'HIGH')
        self.assertIn('PHASE_ALIGNMENT_HEURISTIC', result['confidence_breakdown']['reasons'])

    def test_incomplete_trace_and_reset(self):
        analyzer = FrontSquatAnalyzer()
        frame = {'time': 0, 'displacement': 0}
        for _ in range(1801):
            analyzer._append_phase_frame(frame)
        self.assertEqual(len(analyzer.phase_trace), 1800)
        self.assertEqual(analyzer._aligned_phase_metrics()['reason'], 'TRACE_TRUNCATED')
        analyzer.reset_rep_metrics()
        self.assertFalse(analyzer.phase_trace_truncated)
        self.assertEqual(analyzer.phase_trace, [])
