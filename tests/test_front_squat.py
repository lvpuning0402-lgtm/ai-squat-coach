import unittest

from exercises.front_squat import FrontSquatAnalyzer


class FrontSquatAnalyzerTests(unittest.TestCase):
    @staticmethod
    def frame(
        descent,
        knee_inward=True
    ):
        shoulder_y = (
            0.20
            + descent
        )
        hip_y = (
            0.50
            + descent
        )

        if knee_inward:
            left_knee_x = 0.49
            right_knee_x = 0.51
        else:
            left_knee_x = 0.43
            right_knee_x = 0.57

        return {
            "nose": (
                0.50,
                shoulder_y - 0.10
            ),
            "left_shoulder": (
                0.40,
                shoulder_y
            ),
            "right_shoulder": (
                0.60,
                shoulder_y
            ),
            "left_hip": (
                0.43,
                hip_y
            ),
            "right_hip": (
                0.57,
                hip_y
            ),
            "left_knee": (
                left_knee_x,
                0.70
            ),
            "right_knee": (
                right_knee_x,
                0.70
            ),
            "left_ankle": (
                0.42,
                0.92
            ),
            "right_ankle": (
                0.58,
                0.92
            )
        }

    @staticmethod
    def feed(
        analyzer,
        frame
    ):
        return analyzer.analyze(
            frame["nose"],
            frame["left_shoulder"],
            frame["right_shoulder"],
            frame["left_hip"],
            frame["right_hip"],
            frame["left_knee"],
            frame["right_knee"],
            frame["left_ankle"],
            frame["right_ankle"]
        )

    def test_front_rep_counts_despite_strong_knee_inward_geometry(self):
        analyzer = FrontSquatAnalyzer()

        for _ in range(12):
            self.feed(
                analyzer,
                self.frame(
                    0.0,
                    knee_inward=True
                )
            )

        # Continuous descent with no requirement for a long pause.
        for step in range(1, 19):
            self.feed(
                analyzer,
                self.frame(
                    0.22
                    * step
                    / 18,
                    knee_inward=True
                )
            )

        # Immediate reversal tests the robust bottom latch.
        for step in range(17, -1, -1):
            self.feed(
                analyzer,
                self.frame(
                    0.22
                    * step
                    / 18,
                    knee_inward=True
                )
            )

        completed = False
        completed_summary = None

        for _ in range(12):
            result = self.feed(
                analyzer,
                self.frame(
                    0.0,
                    knee_inward=True
                )
            )

            if result["rep_completed"]:
                completed = True
                completed_summary = result[
                    "rep_summary"
                ]

        self.assertTrue(
            completed
        )
        self.assertEqual(
            analyzer.count,
            1
        )
        self.assertIsNotNone(
            completed_summary
        )
        self.assertIn(
            "phase_metrics",
            completed_summary
        )
        self.assertGreater(
            completed_summary[
                "phase_metrics"
            ][
                "descent"
            ][
                "samples"
            ],
            0
        )
        self.assertGreater(
            completed_summary[
                "phase_metrics"
            ][
                "bottom"
            ][
                "samples"
            ],
            0
        )
        self.assertGreater(
            completed_summary[
                "phase_metrics"
            ][
                "ascent"
            ][
                "samples"
            ],
            0
        )

    def test_front_partial_rep_still_aborts(self):
        analyzer = FrontSquatAnalyzer()

        for _ in range(12):
            self.feed(
                analyzer,
                self.frame(
                    0.0,
                    knee_inward=False
                )
            )

        for step in range(1, 10):
            self.feed(
                analyzer,
                self.frame(
                    0.05
                    * step
                    / 9,
                    knee_inward=False
                )
            )

        aborted = False

        for step in range(8, -1, -1):
            result = self.feed(
                analyzer,
                self.frame(
                    0.05
                    * step
                    / 9,
                    knee_inward=False
                )
            )

            aborted = (
                aborted
                or result["rep_aborted"]
            )

        for _ in range(12):
            result = self.feed(
                analyzer,
                self.frame(
                    0.0,
                    knee_inward=False
                )
            )

            aborted = (
                aborted
                or result["rep_aborted"]
            )

        self.assertTrue(
            aborted
        )
        self.assertEqual(
            analyzer.count,
            0
        )


if __name__ == "__main__":
    unittest.main()
