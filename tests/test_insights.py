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
