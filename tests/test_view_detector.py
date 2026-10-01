import unittest

from pose.view_detector import ViewDetector


class ViewDetectorTests(unittest.TestCase):
    def test_transition_is_entered_before_front(self):
        detector = ViewDetector()

        for _ in range(10):
            view, _, raw = detector.update_from_ratio(
                0.10
            )

        self.assertEqual(
            view,
            "SIDE"
        )

        for _ in range(6):
            view, _, raw = detector.update_from_ratio(
                0.34
            )

        self.assertEqual(
            raw,
            "TRANSITION"
        )
        self.assertEqual(
            view,
            "TRANSITION"
        )

        for _ in range(10):
            view, _, raw = detector.update_from_ratio(
                0.47
            )

        self.assertEqual(
            raw,
            "TRANSITION"
        )
        self.assertEqual(
            view,
            "TRANSITION"
        )

        for _ in range(17):
            view, _, raw = detector.update_from_ratio(
                0.56
            )

        self.assertNotEqual(
            view,
            "FRONT"
        )

        view, _, raw = detector.update_from_ratio(
            0.56
        )

        self.assertEqual(
            raw,
            "FRONT"
        )
        self.assertEqual(
            view,
            "FRONT"
        )

    def test_single_transition_noise_does_not_change_stable_view(self):
        detector = ViewDetector()

        for _ in range(10):
            view, _, raw = detector.update_from_ratio(
                0.56
            )

        self.assertEqual(
            view,
            "FRONT"
        )

        detector.update_from_ratio(
            0.35
        )

        view, _, _ = detector.update_from_ratio(
            0.56
        )

        self.assertEqual(
            view,
            "FRONT"
        )

    def test_side_requires_strict_ratio(self):
        detector = ViewDetector()

        self.assertEqual(
            detector.classify_raw_view(
                0.10
            ),
            "SIDE"
        )
        self.assertEqual(
            detector.classify_raw_view(
                0.30
            ),
            "TRANSITION"
        )
        self.assertEqual(
            detector.classify_raw_view(
                0.46
            ),
            "TRANSITION"
        )
        self.assertEqual(
            detector.classify_raw_view(
                0.56
            ),
            "FRONT"
        )


if __name__ == "__main__":
    unittest.main()
