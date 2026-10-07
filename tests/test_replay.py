from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from reports.replay import main, replay_report
import test_front_alignment as fixtures


class ReplayTests(unittest.TestCase):
    def source(self):
        rep = fixtures.FrontAlignmentTests().run_cycle(pause=8)
        rep['capture_quality'] = {'pose_quality': 'HIGH', 'view_quality': 'HIGH'}
        return {'report_version': 3, 'session_id': 123, 'session_type': 'TEST', 'reps': [rep]}

    def test_replay_preserves_inputs_and_rebuilds_aligned_measurements(self):
        source = self.source()
        before = deepcopy(source)
        result = replay_report(source)
        self.assertEqual(source, before)
        self.assertEqual(result['replay_notes'][0]['status'], 'ALIGNED')
        self.assertEqual(result['reps'][0]['phase_metrics'], source['reps'][0]['phase_metrics'])
        self.assertEqual(result['report_context'], 'OFFLINE_REPLAY')
        self.assertFalse(result['database_written'])

    def test_legacy_report_does_not_invent_trace(self):
        source = self.source()
        source['reps'][0].pop('phase_trace')
        source['reps'][0].pop('phase_alignment')
        result = replay_report(source)
        self.assertEqual(result['replay_notes'][0]['status'], 'LEGACY_AGGREGATES_ONLY')
        self.assertNotIn('phase_trace', result['reps'][0])

    def test_bad_trace_is_rejected_without_mutation(self):
        for corruption in ({'time': 0}, None):
            source = self.source()
            source['reps'][0]['phase_trace'][0] = corruption
            with self.assertRaises(ValueError):
                replay_report(source)

    def test_cli_never_overwrites_source_or_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'session.json'
            original = json.dumps(self.source()).encode()
            path.write_bytes(original)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    main([str(path), '--output', str(path)])
                self.assertEqual(ctx.exception.code, 2)
            self.assertEqual(path.read_bytes(), original)
            output = Path(directory)/'replay.json'
            with redirect_stdout(io.StringIO()):
                main([str(path), '--output', str(output)])
            replay = json.loads(output.read_text())
            self.assertEqual(len(replay['source_sha256']), 64)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['replay.json', 'session.json'])
            self.assertEqual(path.read_bytes(), original)

    def test_empty_trace_cannot_retain_successful_alignment(self):
        source = self.source()
        source['reps'][0]['phase_trace'] = []
        result = replay_report(source)
        self.assertEqual(result['replay_notes'][0]['status'], 'UNAVAILABLE')
        self.assertEqual(result['reps'][0]['detail_confidence'], 'LOW')

    def test_falsey_trace_and_boolean_measurements_are_rejected(self):
        for trace in (None, False, {}, ''):
            source = self.source()
            source['reps'][0]['phase_trace'] = trace
            with self.assertRaises(ValueError):
                replay_report(source)
        source = self.source()
        source['reps'][0]['phase_trace'][0]['time'] = True
        with self.assertRaises(ValueError):
            replay_report(source)

    def test_html_output_and_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.json'
            source.write_text(json.dumps(self.source()), encoding='utf-8')
            html = Path(directory)/'review.html'
            output = Path(directory)/'result.json'
            with redirect_stdout(io.StringIO()):
                main([str(source), '--html', str(html)])
            self.assertIn('离线复核', html.read_text(encoding='utf-8'))
            with redirect_stderr(io.StringIO()):
                for args in ([str(source), '--output', str(output), '--html', str(html)],
                             [str(source), '--output', str(output), '--html', str(output)]):
                    with self.assertRaises(SystemExit):
                        main(args)
            self.assertFalse(output.exists())

    def test_html_escapes_content_and_hides_unreliable_scores(self):
        from reports.review_html import render_review_html
        result = replay_report(self.source())
        result['coach_feedback']['headline'] = '<script>alert(1)</script>'
        rep = result['reps'][0]
        rep['detail_confidence'] = 'LOW'
        rep['detail_score'] = 98.765
        for data in rep['phase_scores'].values():
            data['score'] = 98.765
            data['confidence'] = 'MEDIUM'
        rep['confidence_breakdown']['pose_quality'] = 'LOW'
        html = render_review_html(result)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('约 99', html.split('<h2>逐次结果</h2>')[1])
        self.assertIn('证据不足', html)
