import unittest

import fan_daemon


class FanCurveInterpolationTests(unittest.TestCase):
    def setUp(self):
        self.points = [
            {"temp": 40, "level": 0},
            {"temp": 50, "level": 1},
            {"temp": 60, "level": 2},
            {"temp": 70, "level": 3},
            {"temp": 80, "level": 4},
        ]

    def test_clamps_below_and_above_curve(self):
        self.assertEqual(fan_daemon.interpolate(self.points, 20), 0)
        self.assertEqual(fan_daemon.interpolate(self.points, 95), 4)

    def test_interpolates_between_stages(self):
        self.assertEqual(fan_daemon.interpolate(self.points, 45), 1)
        self.assertEqual(fan_daemon.interpolate(self.points, 65), 2)

    def test_accepts_unsorted_points(self):
        self.assertEqual(fan_daemon.interpolate(list(reversed(self.points)), 65), 2)

    def test_rejects_duplicate_or_too_close_temperatures(self):
        points = [{"temp": 40, "level": 0}, {"temp": 41, "level": 2}]
        with self.assertRaises(ValueError):
            fan_daemon.interpolate(points, 40.5)

    def test_rejects_out_of_range_levels(self):
        points = [{"temp": 40, "level": 0}, {"temp": 50, "level": 5}]
        with self.assertRaises(ValueError):
            fan_daemon.interpolate(points, 45)

    def test_rejects_too_few_points(self):
        with self.assertRaises(ValueError):
            fan_daemon.interpolate([{"temp": 40, "level": 0}], 45)


if __name__ == "__main__":
    unittest.main()
