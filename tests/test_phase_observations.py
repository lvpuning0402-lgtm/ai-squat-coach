import unittest
from feedback.phase_observations import summarize_phase_observations


def rep(number=1, view='SIDE', bottom=95, bottom_confidence='MEDIUM'):
    return {'rep': number, 'view': view, 'detail_confidence': 'LOW',
            'confidence_breakdown': {'pose_quality': 'HIGH', 'view_quality': 'HIGH'},
            'phase_scores': {
                'descent': {'score': 70, 'confidence': 'LOW', 'samples': 20},
                'bottom': {'score': bottom, 'confidence': bottom_confidence, 'samples': 7},
                'ascent': {'score': 92, 'confidence': 'MEDIUM', 'samples': 25}}}


class PhaseObservationTests(unittest.TestCase):
    def test_partial_phases_survive_without_upgrading_overall_confidence(self):
        item = rep()
        phases = summarize_phase_observations([item])['SIDE']
        self.assertIsNone(phases['descent']['score'])
        self.assertEqual(phases['bottom']['score'], 95)
        self.assertEqual(phases['bottom']['confidence'], 'MEDIUM')
        self.assertEqual(phases['ascent']['rep_ids'], [1])
        self.assertEqual(item['detail_confidence'], 'LOW')

    def test_views_and_different_phase_cohorts_remain_separate(self):
        items = [rep(1, bottom=90), rep(2, bottom=10, bottom_confidence='LOW'),
                 rep(3, view='FRONT', bottom=80)]
        result = summarize_phase_observations(items)
        self.assertEqual(result['SIDE']['bottom']['score'], 90)
        self.assertEqual(result['SIDE']['bottom']['rep_ids'], [1])
        self.assertEqual(result['SIDE']['ascent']['rep_ids'], [1, 2])
        self.assertEqual(result['FRONT']['bottom']['score'], 80)
        self.assertEqual(result['SIDE']['bottom']['excluded_reps'], 1)

    def test_low_capture_and_unknown_capture_never_supply_observations(self):
        for label in ('LOW', 'UNKNOWN', None):
            item = rep()
            item['confidence_breakdown']['pose_quality'] = label
            self.assertIsNone(summarize_phase_observations([item])['SIDE']['bottom']['score'])

    def test_nan_missing_and_one_sample_are_excluded(self):
        items = [rep(1, bottom=float('nan')), rep(2, bottom=None), rep(3)]
        items[2]['phase_scores']['bottom']['samples'] = 1
        phase = summarize_phase_observations(items)['SIDE']['bottom']
        self.assertEqual(phase['evaluated_reps'], 0)
        self.assertEqual(phase['excluded_reps'], 3)
        self.assertIsNone(phase['score'])

    def test_excluded_reps_do_not_enter_denominator(self):
        item = rep()
        item['set_valid'] = False
        self.assertEqual(summarize_phase_observations([item]), {})

    def test_medium_evidence_is_not_outvoted(self):
        phases = summarize_phase_observations([rep(i, bottom_confidence='HIGH') for i in range(4)] + [rep(5)])
        self.assertEqual(phases['SIDE']['bottom']['confidence'], 'MEDIUM')
