import time
import unittest

from exercises.side_squat import SideSquatAnalyzer


class SideSquatPhaseMetricTests(unittest.TestCase):
    def test_phase_metrics_are_preserved_in_completed_rep(self):
        analyzer = SideSquatAnalyzer()
        analyzer.count = 1
        analyzer.rep_start_time = (
            time.perf_counter()
            - 2.0
        )
        analyzer.descent_start_time = (
            analyzer.rep_start_time
        )
        analyzer.bottom_start_time = (
            analyzer.rep_start_time
            + 0.9
        )
        analyzer.ascent_start_time = (
            analyzer.rep_start_time
            + 1.1
        )

        analyzer._record_phase_metrics(
            "DESCENDING",
            120.0,
            85.0,
            18.0,
            22.0,
            0.12,
            0.08,
            None,
            -0.10
        )
        analyzer._record_phase_metrics(
            "BOTTOM",
            82.0,
            62.0,
            28.0,
            30.0,
            0.15,
            0.10,
            None,
            0.03
        )
        analyzer._record_phase_metrics(
            "ASCENDING",
            168.0,
            150.0,
            20.0,
            18.0,
            0.10,
            0.06,
            0.07,
            0.02
        )

        analyzer.current_min_knee_angle = 82.0
        analyzer.current_min_hip_angle = 62.0
        analyzer.current_max_knee_angle = 168.0
        analyzer.current_max_depth_margin = 0.03

        rep = analyzer.complete_rep(
            time.perf_counter()
        )

        self.assertIn(
            "phase_metrics",
            rep
        )
        self.assertEqual(
            rep[
                "phase_metrics"
            ][
                "bottom"
            ][
                "samples"
            ],
            1
        )
        self.assertEqual(
            rep[
                "phase_metrics"
            ][
                "bottom"
            ][
                "max_depth_margin"
            ],
            0.03
        )
        self.assertEqual(
            rep[
                "phase_metrics"
            ][
                "ascent"
            ][
                "max_ascent_sync_error"
            ],
            0.07
        )


if __name__ == "__main__":
    unittest.main()
