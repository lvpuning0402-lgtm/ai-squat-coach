import unittest
from feedback.framing import framing_hint, GROUPS


class FramingTests(unittest.TestCase):
    def points(self):
        return {i: {'point': (.5, .5), 'visibility': .9} for i, _ in GROUPS}

    def test_visibility_does_not_claim_full_body_clearance(self):
        hint = framing_hint(self.points(), 'FRONT')
        self.assertEqual(hint['status'], 'VISIBLE')
        self.assertIn('keypoints', hint['message'])

    def test_outside_unclear_and_edge_are_distinguished(self):
        for point, visibility, status in [((.5, 1.1), .9, 'OUT_OF_FRAME'),
                                           ((.5, .5), .5, 'LOW_VISIBILITY'),
                                           ((.5, .98), .9, 'NEAR_EDGE')]:
            points = self.points()
            points[27] = {'point': point, 'visibility': visibility}
            result = framing_hint(points, 'FRONT')
            self.assertEqual(result['status'], status)
            self.assertIn('ANKLES', result['message'])

    def test_side_uses_active_leg_and_no_pose_rejects_stale_points(self):
        points = self.points()
        points[28]['visibility'] = 0
        self.assertEqual(framing_hint(points, 'SIDE', 'LEFT')['status'], 'VISIBLE')
        self.assertEqual(framing_hint(points, 'SIDE', 'RIGHT')['status'], 'LOW_VISIBILITY')
        self.assertEqual(framing_hint(points, 'FRONT', detected=False)['status'], 'NO_POSE')

    def test_missing_or_invalid_points_are_unclear(self):
        for item in (None, {'point': (float('nan'), .5)}, {'point': None}):
            points = self.points()
            points[0] = item
            self.assertEqual(framing_hint(points, 'FRONT')['status'], 'LOW_VISIBILITY')
