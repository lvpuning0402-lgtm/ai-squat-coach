import unittest

from feedback.competition_detail import CompetitionDetailEvaluator
from feedback.performance import SessionPerformanceAnalyzer


class CompetitionDetailEvaluatorTests(unittest.TestCase):
    def test_front_detail_can_warn_while_hard_standard_still_passes(self):
        evaluator = CompetitionDetailEvaluator()

        result = evaluator.evaluate({
            "view": "FRONT",
            "max_left_inward": 0.05,
            "max_right_inward": 0.06,
            "max_ascent_sync_error": 0.08,
            "max_head_shift": 0.10,
            "max_shoulder_tilt": 0.12,
            "max_hip_tilt": 0.11,
            "max_center_shift": 0.11,
            "max_knee_angle_asymmetry": 14.0,
            "max_symmetry_value": 0.20,
        })

        self.assertEqual(
            result["checks"]["knee_tracking"]["state"],
            "PASS"
        )
        self.assertEqual(
            result["checks"]["shoulder_level"]["state"],
            "WATCH"
        )
        self.assertEqual(
            result["checks"]["hip_level"]["state"],
            "WATCH"
        )
        self.assertIn(
            "shoulder_level",
            result["detail_warnings"]
        )
        self.assertLess(
            result["detail_score"],
            100.0
        )

    def test_side_reports_ipf_proxy_and_multiple_angles(self):
        evaluator = CompetitionDetailEvaluator()

        result = evaluator.evaluate({
            "view": "SIDE",
            "depth_standard_met": True,
            "ipf_depth_proxy_met": False,
            "max_ascent_sync_error": 0.10,
            "max_head_forward": 0.23,
            "max_knee_angle": 162.0,
            "min_knee_angle": 82.0,
            "min_hip_angle": 64.0,
            "max_trunk_lean": 31.0,
            "shin_angle_at_min_knee": 28.0,
            "max_depth_margin": -0.02,
        })

        self.assertEqual(
            result["checks"]["general_depth"]["state"],
            "PASS"
        )
        self.assertEqual(
            result["checks"]["ipf_depth_proxy"]["state"],
            "REVIEW"
        )
        self.assertEqual(
            result["checks"]["lockout_proxy"]["state"],
            "WATCH"
        )
        self.assertEqual(
            result["checks"]["trunk_lean_angle"]["state"],
            "INFO"
        )
        self.assertEqual(
            result["angle_metrics"]["shin_angle_at_depth_deg"],
            28.0
        )
        self.assertTrue(
            result["competition_lenses"]["ipf_squat_proxy"][
                "partial_proxy"
            ]
        )


    def test_weighted_front_score_uses_continuous_component_scores(self):
        evaluator = CompetitionDetailEvaluator()

        result = evaluator.evaluate({
            "view": "FRONT",
            "max_left_inward": 0.12,
            "max_right_inward": 0.12,
            "max_ascent_sync_error": 0.10,
            "max_head_shift": 0.09,
            "max_shoulder_tilt": 0.12,
            "max_hip_tilt": 0.10,
            "max_center_shift": 0.09,
            "max_knee_angle_asymmetry": 12.0,
            "max_symmetry_value": 0.18,
        })

        knee = result[
            "checks"
        ][
            "knee_tracking"
        ]

        shoulder = result[
            "checks"
        ][
            "shoulder_level"
        ]

        self.assertEqual(
            knee[
                "state"
            ],
            "WATCH"
        )
        self.assertGreater(
            knee[
                "score"
            ],
            70.0
        )
        self.assertLess(
            knee[
                "score"
            ],
            90.0
        )
        self.assertGreater(
            result[
                "weighted_components"
            ][
                "knee_tracking"
            ][
                "weight"
            ],
            result[
                "weighted_components"
            ][
                "shoulder_level"
            ][
                "weight"
            ]
        )
        self.assertGreater(
            shoulder[
                "score"
            ],
            70.0
        )
        self.assertIn(
            result[
                "detail_grade"
            ],
            [
                "A+",
                "A",
                "B+",
                "B",
                "C+",
                "C",
                "D",
                "E",
            ]
        )

    def test_ipf_proxy_score_is_separate_from_general_coach_score(self):
        evaluator = CompetitionDetailEvaluator()

        result = evaluator.evaluate({
            "view": "SIDE",
            "depth_standard_met": True,
            "ipf_depth_proxy_met": False,
            "max_ascent_sync_error": 0.06,
            "max_head_forward": 0.12,
            "max_knee_angle": 170.0,
            "min_knee_angle": 80.0,
            "min_hip_angle": 60.0,
            "max_trunk_lean": 30.0,
            "shin_angle_at_min_knee": 25.0,
            "max_depth_margin": -0.02,
        })

        self.assertGreater(
            result[
                "detail_score"
            ],
            result[
                "competition_lenses"
            ][
                "ipf_squat_proxy"
            ][
                "score"
            ]
        )
        self.assertIn(
            "ipf_depth_proxy",
            result[
                "competition_flags"
            ]
        )
        self.assertNotIn(
            "ipf_depth_proxy",
            result[
                "detail_warnings"
            ]
        )

class CompetitionDetailPerformanceIntegrationTests(unittest.TestCase):
    def test_detail_score_does_not_change_hard_standard_pass(self):
        analyzer = SessionPerformanceAnalyzer()

        rep = analyzer.analyze_rep({
            "rep": 1,
            "view": "FRONT",
            "total_time": 2.0,
            "max_left_inward": 0.04,
            "max_right_inward": 0.05,
            "max_ascent_sync_error": 0.08,
            "max_head_shift": 0.13,
            "max_shoulder_tilt": 0.14,
            "max_hip_tilt": 0.12,
            "max_center_shift": 0.12,
            "max_knee_angle_asymmetry": 15.0,
            "max_symmetry_value": 0.22,
        })

        self.assertTrue(
            rep["standard_met"]
        )
        self.assertGreater(
            len(
                rep["detail_warnings"]
            ),
            0
        )
        self.assertLess(
            rep["detail_score"],
            100.0
        )

        summary = analyzer.get_set_summary()

        self.assertEqual(
            summary["standard_passes"],
            1
        )
        self.assertEqual(
            summary["detail_watch_reps"],
            1
        )
        self.assertNotEqual(
            summary["top_detail_warning"],
            "NONE"
        )
        self.assertGreaterEqual(
            summary["detail_watch_events"],
            1
        )
        self.assertEqual(
            summary["detail_review_events"],
            0
        )
        self.assertGreaterEqual(
            len(
                summary["top_detail_warnings"]
            ),
            1
        )
        self.assertIsNotNone(
            summary[
                "average_front_physique_score"
            ]
        )
        self.assertIn(
            "knee_tracking",
            summary[
                "detail_component_averages"
            ]
        )


if __name__ == "__main__":
    unittest.main()
