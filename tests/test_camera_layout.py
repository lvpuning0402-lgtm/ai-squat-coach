import unittest
from unittest.mock import patch
import numpy as np
from camera.camera import draw_interface, draw_panel
from feedback.performance import SessionPerformanceAnalyzer


class CameraLayoutTests(unittest.TestCase):
    def test_panels_leave_footer_clear_and_do_not_overlap(self):
        for width, height in [(640, 360), (640, 480), (1280, 720)]:
            for mode in ['SIMPLE', 'DETAIL', 'DEBUG']:
                for count in [3, 18]:
                    frame = np.full((height, width, 3), 160, dtype=np.uint8)
                    boxes = []
                    def panel(frame, title, lines, x, y, width, **kwargs):
                        h = draw_panel(frame, title, lines, x, y, width, **kwargs)
                        boxes.append((x, y, x + width, y + h))
                        return h
                    with patch('camera.camera.draw_panel', side_effect=panel):
                        draw_interface(frame, mode, 'FRONT', 'FRONT', .8, 'VISIBLE',
                                       ['State: ready'] * count, ['State: ready'] * count,
                                       ['Form: ready'] * count, ['Data: ready'] * count,
                                       None, SessionPerformanceAnalyzer(), 'TEST')
                    self.assertTrue(np.all(frame[height - 119:] == 160))
                    for i, (left, top, right, bottom) in enumerate(boxes):
                        self.assertLessEqual(bottom, height - 120)
                        for l, t, r, b in boxes[i + 1:]:
                            self.assertFalse(left < r and l < right and top < b and t < bottom)
