import json
import tempfile
import unittest
from pathlib import Path

from reports.session_report import SessionReportExporter


class SessionReportExporterTests(unittest.TestCase):
    def test_build_and_export_session_report(self):
        reps = [
            {
                "rep": 1,
                "view": "FRONT",
                "quality_score": 92.0,
                "quality_label": "STABLE",
                "descent_time": 1.0,
                "bottom_time": 0.2,
                "ascent_time": 1.1,
                "total_time": 2.3,
                "issues": [],
                "max_left_inward": 0.03,
                "max_right_inward": 0.04,
                "max_symmetry_value": 0.20
            },
            {
                "rep": 2,
                "view": "SIDE",
                "quality_score": 78.0,
                "quality_label": "GOOD",
                "descent_time": 1.2,
                "bottom_time": 0.3,
                "ascent_time": 1.4,
                "total_time": 2.9,
                "issues": [
                    "TRUNK"
                ],
                "min_knee_angle": 105.0,
                "max_trunk_lean": 22.0
            }
        ]

        summary = {
            "reps": 2,
            "average_score": 85.0,
            "best_rep": 1,
            "tempo_change": 0.0,
            "quality_change": 0.0,
            "trend": "COLLECTING",
            "top_issue": "TRUNK"
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = SessionReportExporter(
                temp_dir
            )

            result = exporter.export_session(
                7,
                reps,
                summary,
                session_type="TRAINING"
            )

            json_path = Path(
                result["json"]
            )
            csv_path = Path(
                result["csv"]
            )

            self.assertTrue(
                json_path.exists()
            )
            self.assertTrue(
                csv_path.exists()
            )

            with json_path.open(
                "r",
                encoding="utf-8"
            ) as handle:
                report = json.load(
                    handle
                )

            self.assertEqual(
                report["session_id"],
                7
            )
            self.assertEqual(
                report["session_type"],
                "TRAINING"
            )
            self.assertEqual(
                report["summary"]["reps"],
                2
            )
            self.assertEqual(
                report["view_summary"]["FRONT"]["reps"],
                1
            )
            self.assertEqual(
                report["view_summary"]["SIDE"]["reps"],
                1
            )
            self.assertEqual(
                report["issue_counts"]["TRUNK"],
                1
            )
            self.assertIn(
                "coach_feedback",
                report
            )
            self.assertIn(
                "headline",
                report[
                    "coach_feedback"
                ]
            )
            self.assertIn(
                "next_action",
                report[
                    "coach_feedback"
                ]
            )
            self.assertEqual(
                report[
                    "report_version"
                ],
                3
            )
            self.assertIn(
                "score_explanation",
                report
            )
            self.assertEqual(
                report[
                    "score_explanation"
                ][
                    "method"
                ],
                "WEIGHTED_CONTINUOUS_DEDUCTION"
            )
            self.assertIn(
                "formula",
                report[
                    "score_explanation"
                ]
            )


if __name__ == "__main__":
    unittest.main()

class AutomaticHtmlTests(unittest.TestCase):
    def test_session_html_matches_saved_report_without_replay_label(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            exporter = SessionReportExporter(directory)
            result = exporter.export_session(37, [], {}, session_type='TEST')
            self.assertIsNone(result['html_error'])
            html = Path(result['html']).read_text(encoding='utf-8')
            raw = Path(result['json']).read_bytes()
            self.assertIn('AI SPORT COACH · 训练总结', html)
            self.assertIn('来源训练：37', html)
            self.assertNotIn('使用当前代码重新计算历史报告', html)
            self.assertIn(hashlib.sha256(raw).hexdigest(), html)
            self.assertEqual(Path(result['html']).stem, Path(result['json']).stem)
            self.assertEqual(json.loads(raw), result['report'])

    def test_html_failure_preserves_core_reports(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            exporter = SessionReportExporter(directory)
            with patch.object(exporter, 'export_html', side_effect=OSError('write denied')):
                result = exporter.export_session(38, [], {})
            self.assertIsNone(result['html'])
            self.assertEqual(result['html_error'], 'write denied')
            self.assertTrue(Path(result['json']).is_file())
            self.assertTrue(Path(result['csv']).is_file())

    def test_repeated_exports_have_distinct_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            exporter = SessionReportExporter(directory)
            first = exporter.export_session(39, [], {})
            original = Path(first['json']).read_bytes()
            second = exporter.export_session(39, [], {})
            self.assertNotEqual(first['json'], second['json'])
            self.assertEqual(Path(first['json']).read_bytes(), original)
