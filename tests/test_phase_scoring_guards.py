import unittest

from feedback.competition_detail import CompetitionDetailEvaluator
from feedback.performance import SessionPerformanceAnalyzer
from feedback.insights import SessionInsightBuilder


def side_rep(bottom_depth=-.2, rep_depth=.18):
    common = dict(samples=12, min_trunk_lean=10, max_trunk_lean=38,
                  max_head_forward=.12, max_knee_angle=174,
                  max_ascent_sync_error=.04)
    return dict(view='SIDE', rep=1, total_time=3, descent_time=1.4,
                bottom_time=.2, ascent_time=1.4, max_depth_margin=rep_depth,
                depth_standard_met=rep_depth >= -.08,
                ipf_depth_proxy_met=rep_depth >= 0,
                max_head_forward=.12, max_knee_angle=174,
                max_ascent_sync_error=.04, min_knee_angle=65,
                capture_quality=dict(pose_quality='HIGH', view_quality='HIGH'),
                phase_metrics=dict(
                    descent=dict(common, max_depth_margin=rep_depth),
                    bottom=dict(common, samples=3, min_trunk_lean=37,
                                max_depth_margin=bottom_depth),
                    ascent=dict(common, max_depth_margin=-.4)))


class PhaseScoringGuardTests(unittest.TestCase):
    def test_delayed_bottom_is_not_a_depth_failure(self):
        result = CompetitionDetailEvaluator().evaluate(side_rep())
        bottom = result['phase_scores']['bottom']
        self.assertEqual(bottom['checks']['general_depth']['state'], 'INFO')
        self.assertIsNone(bottom['checks']['general_depth']['score'])
        self.assertNotIn('general_depth', bottom['weighted_components'])
        self.assertEqual(bottom['confidence'], 'LOW')
        self.assertIsNone(result['weakest_phase'])
        self.assertIn('BOTTOM_DEPTH_PHASE_MISMATCH',
                      result['confidence_breakdown']['reasons'])
        self.assertEqual(result['checks']['general_depth']['state'], 'PASS')

    def test_missing_depth_is_not_a_failure(self):
        rep = side_rep()
        del rep['phase_metrics']['bottom']['max_depth_margin']
        result = CompetitionDetailEvaluator().evaluate(rep)
        self.assertIsNone(result['phase_scores']['bottom']['checks']['general_depth']['score'])
        self.assertIn('BOTTOM_DEPTH_MISSING', result['confidence_breakdown']['reasons'])

    def test_consistently_shallow_depth_still_scores(self):
        result = CompetitionDetailEvaluator().evaluate(side_rep(-.3, -.2))
        self.assertEqual(result['phase_scores']['bottom']['checks']['general_depth']['state'], 'REVIEW')

    def test_aligned_depth_keeps_measured_bottom_samples(self):
        result = CompetitionDetailEvaluator().evaluate(side_rep(.18, .18))
        self.assertEqual(result['phase_scores']['bottom']['checks']['general_depth']['score'], 100)
        self.assertEqual(result['phase_scores']['bottom']['samples'], 3)

    def test_motion_range_does_not_deduct_or_inflate_coverage(self):
        result = CompetitionDetailEvaluator().evaluate(side_rep(.18, .18))
        for name in ('descent', 'ascent'):
            phase = result['phase_scores'][name]
            self.assertEqual(phase['checks']['trunk_stability']['state'], 'INFO')
            self.assertNotIn('trunk_stability', phase['weighted_components'])
            self.assertNotIn('trunk_stability', phase['warnings'])
            self.assertLess(phase['coverage'], 1)
        self.assertEqual(result['phase_scores']['descent']['confidence'], 'LOW')

    def test_conflict_reaches_coach_and_best_rep_selection(self):
        analyzer = SessionPerformanceAnalyzer()
        rep = analyzer.analyze_rep(side_rep())
        summary = analyzer.get_set_summary()
        self.assertIsNone(summary['best_detail_rep'])
        self.assertIsNone(summary['weakest_phase'])
        coach = SessionInsightBuilder().build([rep], summary)
        self.assertEqual(coach['confidence'], 'LOW')


if __name__ == '__main__':
    unittest.main()
