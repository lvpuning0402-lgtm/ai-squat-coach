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

        transition_reached = False

        for _ in range(12):
            view, _, raw = detector.update_from_ratio(
                0.34
            )

            if view == "TRANSITION":
                transition_reached = True
                break

        self.assertTrue(
            transition_reached
        )
        self.assertEqual(
            raw,
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

        # 因为有 7 帧中值平滑 + 18 帧稳定确认，
        # 刚进入正面区时不能立刻切换到 FRONT。
        for _ in range(10):
            view, _, raw = detector.update_from_ratio(
                0.56
            )

        self.assertEqual(
            raw,
            "FRONT"
        )
        self.assertNotEqual(
            view,
            "FRONT"
        )

        front_reached = False

        for _ in range(20):
            view, _, raw = detector.update_from_ratio(
                0.56
            )

            if view == "FRONT":
                front_reached = True
                break

        self.assertTrue(
            front_reached
        )
        self.assertEqual(
            raw,
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

    def test_front_to_side_also_passes_through_transition(self):
        detector = ViewDetector()

        for _ in range(10):
            view, _, raw = detector.update_from_ratio(
                0.56
            )

        self.assertEqual(
            view,
            "FRONT"
        )

        transition_reached = False

        for _ in range(12):
            view, _, raw = detector.update_from_ratio(
                0.34
            )

            if view == "TRANSITION":
                transition_reached = True
                break

        self.assertTrue(
            transition_reached
        )

        side_reached = False

        for _ in range(30):
            view, _, raw = detector.update_from_ratio(
                0.10
            )

            if view == "SIDE":
                side_reached = True
                break

        self.assertTrue(
            side_reached
        )


if __name__ == "__main__":
    unittest.main()
