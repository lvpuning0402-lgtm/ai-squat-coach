import unittest

from feedback.insights import (
    ProgressInsightBuilder,
    SessionInsightBuilder,
)


class SessionInsightBuilderTests(unittest.TestCase):
    def test_front_knee_tracking_becomes_primary_coach_focus(self):
        builder = SessionInsightBuilder()

        reps = []

        for index in range(
            1,
            7
        ):
            knee_ok = index <= 3

            reps.append({
                "rep": index,
                "view": "FRONT",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": knee_ok,
                "standard_checks": {
                    "knee_tracking": knee_ok,
                    "ascent_control": True
                },
                "issues": (
                    []
                    if knee_ok
                    else [
                        "KNEE_TRACKING"
                    ]
                )
            })

        summary = {
            "excluded_reps": 0
        }

        result = builder.build(
            reps,
            summary,
            session_type="TEST"
        )

        self.assertEqual(
            result["main_issue"],
            "KNEE_TRACKING"
        )
        self.assertEqual(
            result["standard_pass_rate"],
            50.0
        )
        self.assertEqual(
            result["metrics"][
                "front_knee_tracking_failures"
            ],
            3
        )
        self.assertEqual(
            result["metrics"][
                "ascent_control_passes"
            ],
            6
        )
        self.assertIn(
            "膝盖",
            result["next_action"]
        )
        self.assertTrue(
            result["test_protocol"]
        )

    def test_side_depth_feedback_reports_depth_pass_count(self):
        builder = SessionInsightBuilder()

        reps = []

        for index in range(
            1,
            5
        ):
            depth_ok = index <= 2

            reps.append({
                "rep": index,
                "view": "SIDE",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": depth_ok,
                "standard_checks": {
                    "depth": depth_ok,
                    "ascent_control": True
                },
                "issues": (
                    []
                    if depth_ok
                    else [
                        "DEPTH"
                    ]
                )
            })

        result = builder.build(
            reps,
            {
                "excluded_reps": 0
            },
            session_type="TRAINING"
        )

        self.assertEqual(
            result["main_issue"],
            "DEPTH"
        )
        self.assertEqual(
            result["metrics"][
                "side_depth_passes"
            ],
            2
        )
        self.assertIn(
            "2/4",
            result["focus"]
        )

    def test_issue_frequency_beats_priority_when_counts_differ(self):
        builder = SessionInsightBuilder()

        reps = [
            {
                "view": "FRONT",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": False,
                "standard_checks": {
                    "knee_tracking": False,
                    "ascent_control": True
                },
                "issues": [
                    "KNEE_TRACKING"
                ]
            },
            {
                "view": "SIDE",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": False,
                "standard_checks": {
                    "depth": False,
                    "ascent_control": True
                },
                "issues": [
                    "DEPTH"
                ]
            },
            {
                "view": "SIDE",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": False,
                "standard_checks": {
                    "depth": False,
                    "ascent_control": True
                },
                "issues": [
                    "DEPTH"
                ]
            }
        ]

        result = builder.build(
            reps,
            {
                "excluded_reps": 0
            },
            session_type="TRAINING"
        )

        self.assertEqual(
            result["main_issue"],
            "DEPTH"
        )


    def test_detail_warning_becomes_coach_focus_when_standard_passes(self):
        builder = SessionInsightBuilder()

        reps = [
            {
                "rep": 1,
                "view": "FRONT",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": True,
                "standard_checks": {
                    "knee_tracking": True,
                    "ascent_control": True
                },
                "issues": [],
                "detail_warnings": [
                    "shoulder_level"
                ]
            },
            {
                "rep": 2,
                "view": "FRONT",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": True,
                "standard_checks": {
                    "knee_tracking": True,
                    "ascent_control": True
                },
                "issues": [],
                "detail_warnings": [
                    "shoulder_level"
                ]
            }
        ]

        result = builder.build(
            reps,
            {
                "excluded_reps": 0
            },
            session_type="TRAINING"
        )

        self.assertEqual(
            result["main_issue"],
            "NONE"
        )
        self.assertEqual(
            result["detail_focus"],
            "shoulder_level"
        )
        self.assertIn(
            "肩线水平",
            result["headline"]
        )
        self.assertIn(
            "肩线",
            result["next_action"]
        )


    def test_mixed_detail_severities_report_separate_counts(self):
        reps = [{"rep": i, "view": "FRONT", "standard_met": True,
                 "issues": [], "detail_warnings": ["knee_angle_symmetry"],
                 "detail_checks": {"knee_angle_symmetry": {"state": state}}}
                for i, state in enumerate(["REVIEW"] * 4 + ["WATCH"], 1)]
        result = SessionInsightBuilder().build(reps, {}, "TEST")
        self.assertEqual(result["detail_focus_counts"],
                         {"review": 4, "watch": 1, "total": 5})
        self.assertIn("需复核 4 次，留意 1 次", result["focus"])
        self.assertEqual(result["detail_focus_severity"], "REVIEW")
        reps[0]["set_valid"] = False
        result = SessionInsightBuilder().build(reps, {}, "TEST")
        self.assertEqual(result["detail_focus_counts"],
                         {"review": 3, "watch": 1, "total": 4})

    def test_session_feedback_reports_weakest_phase(self):
        builder = SessionInsightBuilder()

        reps = [
            {
                "rep": 1,
                "view": "FRONT",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": True,
                "standard_checks": {
                    "knee_tracking": True,
                    "ascent_control": True
                },
                "issues": [],
                "detail_warnings": []
            },
            {
                "rep": 2,
                "view": "FRONT",
                "analysis_valid": True,
                "set_valid": True,
                "standard_met": True,
                "standard_checks": {
                    "knee_tracking": True,
                    "ascent_control": True
                },
                "issues": [],
                "detail_warnings": []
            }
        ]

        result = builder.build(
            reps,
            {
                "excluded_reps": 0,
                "weakest_phase": {
                    "phase": "bottom",
                    "score": 78.5
                },
                "phase_deduction_summary": {
                    "bottom": [
                        {
                            "name": "center_balance",
                            "average_lost_points": 4.6,
                            "total_lost_points": 9.2,
                            "occurrences": 2
                        }
                    ]
                },
                "top_detail_deductions": [
                    {
                        "name": "center_balance",
                        "average_lost_points": 3.8,
                        "total_lost_points": 7.6,
                        "affected_reps": 2,
                        "occurrences": 2
                    }
                ]
            },
            session_type="TRAINING"
        )

        self.assertEqual(
            result[
                "phase_focus"
            ],
            "bottom"
        )
        self.assertEqual(
            result[
                "phase_focus_score"
            ],
            78.5
        )
        self.assertIn(
            "最低点阶段",
            result[
                "focus"
            ]
        )
        self.assertTrue(
            any(
                "Weak phase" in line
                for line in result[
                    "ui_lines"
                ]
            )
        )
        self.assertEqual(
            result[
                "phase_reason"
            ][
                "name"
            ],
            "center_balance"
        )
        self.assertIn(
            "身体重心稳定",
            result[
                "focus"
            ]
        )
        self.assertTrue(
            any(
                "Why:" in line
                for line in result[
                    "ui_lines"
                ]
            )
        )


class ProgressInsightBuilderTests(unittest.TestCase):
    def test_progress_feedback_uses_formal_baseline_change(self):
        builder = ProgressInsightBuilder()

        result = builder.build({
            "sessions": 4,
            "latest_average_score": 92.0,
            "score_change": 6.0,
            "trend": "IMPROVING",
            "latest_top_issue": "KNEE_TRACKING",
            "latest_top_issue_rate": 25.0
        })

        self.assertIn(
            "高于",
            result["headline"]
        )
        self.assertIn(
            "提高 6.0",
            result["summary"]
        )
        self.assertIn(
            "膝盖轨迹",
            result["focus"]
        )


if __name__ == "__main__":
    unittest.main()
