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
