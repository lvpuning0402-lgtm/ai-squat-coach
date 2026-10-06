import unittest

from camera.camera import (
    _rep_detail_state,
    _rep_timeline_line,
    build_session_summary_frame,
    format_deduction,
    format_phase_scores,
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
            "average_detail_score": 84.0,
            "detail_watch_reps": 1,
            "detail_watch_events": 1,
            "detail_review_events": 1,
            "top_detail_deductions": [
                {
                    "name": "center_balance",
                    "average_lost_points": 3.4,
                    "total_lost_points": 6.8,
                    "affected_reps": 2,
                    "occurrences": 2
                }
            ],
            "phase_deduction_summary": {
                "bottom": [
                    {
                        "name": "center_balance",
                        "average_lost_points": 4.2,
                        "total_lost_points": 8.4,
                        "occurrences": 2
                    }
                ]
            },
            "phase_score_averages": {
                "descent": 88.0,
                "bottom": 76.0,
                "ascent": 91.0,
            },
            "weakest_phase": {
                "phase": "bottom",
                "score": 76.0,
            },
            "top_detail_warnings": [
                {
                    "name": "shoulder_level",
                    "watch": 1,
                    "review": 0,
                    "total": 1
                }
            ],
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

    def test_format_deduction(self):
        self.assertEqual(
            format_deduction({
                "name": "center_balance",
                "average_lost_points": 3.45
            }),
            "center balance -3.5"
        )
        self.assertEqual(
            format_deduction({
                "name": "knee_tracking",
                "lost_points": 2.04
            }),
            "knee tracking -2.0"
        )
        self.assertEqual(
            format_deduction(
                None
            ),
            "--"
        )

    def test_format_phase_scores_supports_summary_and_rep_shapes(self):
        self.assertEqual(
            format_phase_scores({
                "descent": 91.2,
                "bottom": 82.3,
                "ascent": 94.4,
            }),
            "91.2 / 82.3 / 94.4"
        )

        self.assertEqual(
            format_phase_scores({
                "descent": {
                    "score": 91.2
                },
                "bottom": {
                    "score": 82.3
                },
                "ascent": {
                    "score": 94.4
                },
            }),
            "91.2 / 82.3 / 94.4"
        )

    def test_timeline_separates_standard_and_detail_state(self):
        rep = {
            "rep": 1,
            "view": "FRONT",
            "quality_score": 100.0,
            "standard_met": True,
            "issues": [],
            "analysis_valid": True,
            "set_valid": True,
            "detail_warnings": [
                "shoulder_level",
                "center_balance"
            ],
            "detail_checks": {
                "shoulder_level": {
                    "state": "WATCH"
                },
                "center_balance": {
                    "state": "REVIEW"
                }
            }
        }

        detail_state, detail_text = (
            _rep_detail_state(
                rep
            )
        )

        self.assertEqual(
            detail_state,
            "REVIEW"
        )
        self.assertIn(
            "+1",
            detail_text
        )

        line = _rep_timeline_line(
            rep
        )

        self.assertIn(
            "PASS",
            line
        )
        self.assertIn(
            "REVIEW",
            line
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

class IndependentPhaseDisplayTests(unittest.TestCase):
    def test_partial_observation_shows_approximation_and_counts(self):
        from camera.camera import format_phase_observation_lines
        summary = {'phase_observations_by_view': {'SIDE': {
            'descent': {'score': None, 'confidence': 'LOW', 'evaluated_reps': 0},
            'bottom': {'score': 94.5, 'confidence': 'MEDIUM', 'evaluated_reps': 3},
            'ascent': {'score': 92.6, 'confidence': 'MEDIUM', 'evaluated_reps': 3}}}}
        lines = format_phase_observation_lines(summary)
        self.assertIn('~94 / ~93', lines[0])
        self.assertIn('n=0/3/3', lines[0])
        self.assertIn('observations', lines[1])
