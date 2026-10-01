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

    def test_front_knee_tracking_is_standard_and_symmetry_is_diagnostic(self):
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
        self.assertNotIn(
            "ASYMMETRY",
            result["issues"]
        )
        self.assertIn(
            "symmetry_score",
            result["diagnostic_metrics"]
        )
        self.assertFalse(
            result["standard_checks"]["knee_tracking"]
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

    def test_timing_outlier_is_excluded_from_set_summary(self):
        analyzer = SessionPerformanceAnalyzer()

        valid = analyzer.analyze_rep({
            "rep": 1,
            "view": "FRONT",
            "total_time": 1.5,
            "descent_time": 0.8,
            "bottom_time": 0.1,
            "ascent_time": 0.6,
            "rom": 0.43,
            "max_head_shift": 0.05,
            "max_shoulder_tilt": 0.05,
            "max_center_shift": 0.05,
            "max_sync_error": 0.10,
            "max_left_inward": 0.0,
            "max_right_inward": 0.0,
            "max_symmetry_value": 0.15
        })

        invalid = analyzer.analyze_rep({
            "rep": 2,
            "view": "FRONT",
            "total_time": 102.0,
            "descent_time": 95.0,
            "bottom_time": 0.1,
            "ascent_time": 6.9,
            "rom": 0.30,
            "max_head_shift": 0.10,
            "max_shoulder_tilt": 0.20,
            "max_center_shift": 1.10,
            "max_sync_error": 0.20,
            "max_left_inward": 0.30,
            "max_right_inward": 0.40,
            "max_symmetry_value": 0.20
        })

        self.assertTrue(
            valid["analysis_valid"]
        )
        self.assertFalse(
            invalid["analysis_valid"]
        )
        self.assertIn(
            "TEMPO_OUTLIER",
            invalid["confidence_reasons"]
        )

        summary = analyzer.get_set_summary()

        self.assertEqual(
            summary["reps"],
            2
        )
        self.assertEqual(
            summary["valid_reps"],
            1
        )
        self.assertEqual(
            summary["excluded_reps"],
            1
        )
        self.assertEqual(
            summary["best_rep"],
            1
        )

    def test_consistency_uses_tempo_and_front_rom(self):
        analyzer = SessionPerformanceAnalyzer()

        samples = [
            (1.52, 0.440),
            (1.36, 0.408),
            (1.58, 0.436),
            (1.36, 0.446)
        ]

        for index, (
            total_time,
            rom
        ) in enumerate(
            samples,
            start=1
        ):
            analyzer.analyze_rep({
                "rep": index,
                "view": "FRONT",
                "total_time": total_time,
                "descent_time": 0.85,
                "bottom_time": 0.10,
                "ascent_time": 0.50,
                "rom": rom,
                "max_head_shift": 0.05,
                "max_shoulder_tilt": 0.07,
                "max_center_shift": 0.04,
                "max_sync_error": 0.14,
                "max_left_inward": 0.0,
                "max_right_inward": 0.0,
                "max_symmetry_value": 0.15
            })

        summary = analyzer.get_set_summary()

        self.assertEqual(
            summary["valid_reps"],
            4
        )
        self.assertLess(
            summary["front_rom_cv"],
            5.0
        )
        self.assertLess(
            summary["tempo_cv"],
            10.0
        )
        self.assertEqual(
            summary["consistency_label"],
            "CONSISTENT"
        )

    def test_side_trunk_is_diagnostic_and_depth_is_standardized(self):
        analyzer = SessionPerformanceAnalyzer()

        result = analyzer.analyze_rep({
            "rep": 1,
            "view": "SIDE",
            "descent_time": 1.10,
            "bottom_time": 0.10,
            "ascent_time": 0.73,
            "total_time": 1.93,
            "rom_degrees": 118.0,
            "min_knee_angle": 62.0,
            "min_hip_angle": 43.0,
            "max_trunk_lean": 34.0,
            "max_head_forward": 0.34,
            "max_sync_error": 0.12,
            "max_depth_margin": 0.08,
            "depth_standard_met": True
        })

        self.assertNotIn(
            "TRUNK",
            result["issues"]
        )
        self.assertTrue(
            result["standard_checks"]["depth"]
        )
        self.assertTrue(
            result["standard_met"]
        )
        self.assertIn(
            "trunk_lean",
            result["diagnostic_metrics"]
        )
        self.assertNotIn(
            "trunk",
            result["component_scores"]
        )

    def test_side_above_parallel_fails_depth_standard(self):
        analyzer = SessionPerformanceAnalyzer()

        result = analyzer.analyze_rep({
            "rep": 1,
            "view": "SIDE",
            "descent_time": 1.0,
            "bottom_time": 0.1,
            "ascent_time": 0.8,
            "total_time": 1.9,
            "rom_degrees": 75.0,
            "min_knee_angle": 105.0,
            "min_hip_angle": 70.0,
            "max_trunk_lean": 20.0,
            "max_head_forward": 0.20,
            "max_sync_error": 0.10,
            "max_depth_margin": -0.12,
            "depth_standard_met": False
        })

        self.assertIn(
            "DEPTH",
            result["issues"]
        )
        self.assertFalse(
            result["standard_checks"]["depth"]
        )
        self.assertFalse(
            result["standard_met"]
        )

    def test_relative_front_rom_outlier_is_excluded_from_set(self):
        analyzer = SessionPerformanceAnalyzer()

        samples = [
            (3.33, 0.129),
            (1.47, 0.485),
            (2.13, 0.476),
            (1.92, 0.471),
            (1.71, 0.450),
            (1.90, 0.495),
            (1.64, 0.468)
        ]

        for index, (
            total_time,
            rom
        ) in enumerate(
            samples,
            start=1
        ):
            analyzer.analyze_rep({
                "rep": index,
                "view": "FRONT",
                "total_time": total_time,
                "descent_time": 1.0,
                "bottom_time": 0.1,
                "ascent_time": 0.6,
                "rom": rom,
                "max_head_shift": 0.07,
                "max_shoulder_tilt": 0.09,
                "max_center_shift": 0.06,
                "max_sync_error": 0.14,
                "max_left_inward": 0.0,
                "max_right_inward": 0.0,
                "max_symmetry_value": 0.16
            })

        summary = analyzer.get_set_summary()

        self.assertEqual(
            summary["reps"],
            7
        )
        self.assertEqual(
            summary["valid_reps"],
            6
        )
        self.assertEqual(
            summary["relative_excluded_reps"],
            1
        )
        self.assertFalse(
            analyzer.reps[0]["set_valid"]
        )
        self.assertIn(
            "SET_ROM_OUTLIER",
            analyzer.reps[0][
                "set_exclusion_reasons"
            ]
        )


if __name__ == "__main__":
    unittest.main()
