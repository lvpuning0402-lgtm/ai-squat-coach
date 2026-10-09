import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reports.open_latest import latest_report, open_path


class ReportAccessTests(unittest.TestCase):
    def write_report(self, directory, name, date, html=True):
        path = Path(directory) / name
        path.write_text(json.dumps({'session_id': 1, 'generated_at': date}))
        if html:
            path.with_suffix('.html').write_text('report')
        return path.with_suffix('.html')

    def test_latest_uses_report_date_and_skips_replays_and_broken_json(self):
        with tempfile.TemporaryDirectory() as d:
            expected = self.write_report(d, 'session_10.json', '2026-10-09T12:00:00')
            self.write_report(d, 'session_9.json', '2026-10-08T12:00:00')
            Path(d, 'session_broken.json').write_text('{')
            Path(d, 'session_replay.json').write_text(json.dumps({'session_id': 99,
                'generated_at': '2027-01-01', 'report_context': 'OFFLINE_REPLAY'}))
            self.assertEqual(latest_report(d), expected)

    def test_missing_latest_html_does_not_silently_open_old_training(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_report(d, 'session_1.json', '2026-10-01', html=True)
            self.write_report(d, 'session_2.json', '2026-10-02', html=False)
            with self.assertRaises(FileNotFoundError):
                latest_report(d)

    def test_open_report_handles_spaces_without_shell(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / '训练 report.html'
            path.write_text('report')
            with patch('reports.open_latest.webbrowser.open', return_value=True) as browser:
                self.assertTrue(open_path(path))
                browser.assert_called_once_with(path.resolve().as_uri())
