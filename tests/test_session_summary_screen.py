import unittest

from camera.camera import (
    _rep_timeline_line,
    build_session_summary_frame,
)


class SessionSummaryScreenTests(unittest.TestCase):
    def test_build_session_summary_frame(self):
        reps = [
            {
                "rep": 1,
                "view": "FRONT",
                "quality_score": 100.0,
                "standard_met": True,
                "standard_checks": {
                    "knee_tracking": True,
                    "ascent_control": True,
                },
                "issues": [],
                "analysis_valid": True,
                "set_valid": True,
            },
            {
                "rep": 2,
                "view": "FRONT",
                "quality_score": 82.0,
                "standard_met": False,
                "standard_checks": {
                    "knee_tracking": False,
                    "ascent_control": True,
                },
                "issues": [
                    "KNEE_TRACKING"
                ],
                "analysis_valid": True,
                "set_valid": True,
            },
        ]

        summary = {
            "reps": 2,
            "valid_reps": 2,
            "average_score": 91.0,
            "standard_passes": 1,
            "standard_pass_rate": 50.0,
            "best_rep": 1,
            "side_reps": 0,
            "side_depth_passes": 0,
            "side_depth_pass_rate": 0.0,
            "side_ipf_proxy_passes": 0,
            "side_ipf_proxy_rate": 0.0,
            "excluded_reps": 0,
            "consistency_label": "COLLECTING",
            "trend": "COLLECTING",
        }

        frame = build_session_summary_frame(
            reps,
            summary,
            "TEST",
            width=900,
            height=700
        )

        self.assertEqual(
            frame.shape,
            (
                700,
                900,
                3
            )
        )
        self.assertGreater(
            int(
                frame.max()
            ),
            24
        )

    def test_timeline_marks_excluded_rep(self):
        line = _rep_timeline_line({
            "rep": 3,
            "view": "SIDE",
            "quality_score": 70.0,
            "standard_met": False,
            "issues": [
                "DEPTH"
            ],
            "analysis_valid": False,
            "set_valid": True,
        })

        self.assertIn(
            "EXCLUDED",
            line
        )
        self.assertIn(
            "DEPTH",
            line
        )


if __name__ == "__main__":
    unittest.main()
