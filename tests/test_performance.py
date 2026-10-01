import unittest

from feedback.performance import SessionPerformanceAnalyzer


class SessionPerformanceAnalyzerTests(unittest.TestCase):
    def test_front_stable_rep_scores_high(self):
        analyzer = SessionPerformanceAnalyzer()

        result = analyzer.analyze_rep({
            "rep": 1,
            "view": "FRONT",
            "total_time": 3.0,
            "max_head_shift": 0.05,
            "max_shoulder_tilt": 0.04,
            "max_center_shift": 0.05,
            "max_sync_error": 0.04,
            "max_left_inward": 0.02,
            "max_right_inward": 0.03,
            "max_symmetry_value": 0.20
        })

        self.assertGreaterEqual(
            result["quality_score"],
            95.0
        )
        self.assertEqual(
            result["issues"],
            []
        )

    def test_front_knee_in_and_asymmetry_are_reported(self):
        analyzer = SessionPerformanceAnalyzer()

        result = analyzer.analyze_rep({
            "rep": 1,
            "view": "FRONT",
            "total_time": 3.0,
            "max_head_shift": 0.05,
            "max_shoulder_tilt": 0.04,
            "max_center_shift": 0.05,
            "max_sync_error": 0.04,
            "max_left_inward": 0.25,
            "max_right_inward": 0.19,
            "max_symmetry_value": 0.75
        })

        self.assertIn(
            "KNEE_TRACKING",
            result["issues"]
        )
        self.assertIn(
            "ASYMMETRY",
            result["issues"]
        )
        self.assertLess(
            result["quality_score"],
            100.0
        )

    def test_set_summary_reports_top_issue(self):
        analyzer = SessionPerformanceAnalyzer()

        for index in range(4):
            analyzer.analyze_rep({
                "rep": index + 1,
                "view": "FRONT",
                "total_time": 3.0 + index * 0.1,
                "max_head_shift": 0.05,
                "max_shoulder_tilt": 0.04,
                "max_center_shift": 0.05,
                "max_sync_error": 0.04,
                "max_left_inward": 0.22,
                "max_right_inward": 0.18,
                "max_symmetry_value": 0.20
            })

        summary = analyzer.get_set_summary()

        self.assertEqual(
            summary["reps"],
            4
        )
        self.assertEqual(
            summary["top_issue"],
            "KNEE_TRACKING"
        )


if __name__ == "__main__":
    unittest.main()
