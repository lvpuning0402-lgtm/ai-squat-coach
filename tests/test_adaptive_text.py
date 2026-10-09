import unittest
from camera.status_banner import AdaptiveTextColors


class AdaptiveTextTests(unittest.TestCase):
    def test_threshold_noise_keeps_initial_color(self):
        for initial, expected in [(130, (255, 255, 255)), (160, (0, 0, 0))]:
            colors = AdaptiveTextColors()
            colors.color('label', initial, 0)
            for i in range(1, 301):
                self.assertEqual(colors.color('label', 130 if i % 2 else 160, i / 30), expected)

    def test_sustained_change_in_both_directions_at_different_fps(self):
        for fps in (10, 30, 60):
            colors = AdaptiveTextColors()
            self.assertEqual(colors.color('label', 30, 0), (255, 255, 255))
            for i in range(1, 2 * fps + 1):
                ink = colors.color('label', 230, i / fps)
                if i / fps < 1.5:
                    self.assertEqual(ink, (255, 255, 255))
            self.assertEqual(ink, (0, 0, 0))
            for i in range(1, 2 * fps + 1):
                ink = colors.color('label', 30, 2 + i / fps)
            self.assertEqual(ink, (255, 255, 255))

    def test_short_flashes_do_not_switch(self):
        colors = AdaptiveTextColors()
        colors.color('label', 30, 0)
        for i in range(1, 301):
            brightness = 240 if i % 30 < 6 else 30
            self.assertEqual(colors.color('label', brightness, i / 30), (255, 255, 255))

    def test_regions_independent_and_stale_history_expires(self):
        colors = AdaptiveTextColors()
        self.assertEqual(colors.color('a', 30, 0), (255, 255, 255))
        self.assertEqual(colors.color('b', 230, 0), (0, 0, 0))
        self.assertEqual(colors.color('a', 230, 3), (0, 0, 0))
        colors.clear()
        self.assertFalse(colors.states)
