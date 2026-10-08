import unittest
from camera.auto_capture import AutoCapture


class AutoCaptureTests(unittest.TestCase):
    def points(self, x=.5):
        return {0: {'point': (x, .3), 'visibility': .9}}

    def run_hold(self, capture, start=0, view='FRONT'):
        return [capture.update(start + i / 10, view, view, 'VISIBLE', self.points())[0]
                for i in range(41)]

    def test_three_seconds_and_no_repeated_photos(self):
        capture = AutoCapture()
        shots = self.run_hold(capture)
        self.assertFalse(any(shots[:30]))
        self.assertEqual(sum(shots), 1)
        self.assertEqual(sum(self.run_hold(capture, 5)), 0)
        self.assertEqual(sum(self.run_hold(capture, 10, 'SIDE')), 1)
        capture.rearm()
        self.assertEqual(sum(self.run_hold(capture, 20)), 1)

    def test_bad_capture_and_view_change_reset_countdown(self):
        capture = AutoCapture()
        for i in range(25):
            capture.update(i / 10, 'FRONT', 'FRONT', 'VISIBLE', self.points())
        self.assertFalse(capture.update(2.5, 'FRONT', 'FRONT', 'LOW_VISIBILITY', self.points())[0])
        self.assertFalse(capture.update(2.6, 'FRONT', 'TRANSITION', 'VISIBLE', self.points())[0])
        shots = self.run_hold(capture, 2.7)
        self.assertFalse(any(shots[:30]))
        self.assertEqual(sum(shots), 1)

    def test_motion_and_camera_gap_restart_hold(self):
        capture = AutoCapture()
        for i in range(25):
            capture.update(i / 10, 'FRONT', 'FRONT', 'VISIBLE', self.points())
        self.assertFalse(capture.update(2.5, 'FRONT', 'FRONT', 'VISIBLE', self.points(.6))[0])
        self.assertEqual(capture.started, 2.5)
        self.assertFalse(capture.update(8, 'FRONT', 'FRONT', 'VISIBLE', self.points(.6))[0])
        self.assertEqual(capture.started, 8)
