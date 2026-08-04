import unittest

from peripatetic_timetable.presentation.timetable_view import calculate_layout


class TimetableLayoutTests(unittest.TestCase):
    def test_complete_grid_fits_common_scaled_windows_viewport(self):
        for width, height in ((1240, 430), (1100, 520), (1600, 700)):
            with self.subTest(width=width, height=height):
                layout = calculate_layout(width, height, 6)
                self.assertLessEqual(layout.total_width, width)
                total_height = (
                    layout.margin * 2
                    + layout.header_height
                    + sum(layout.row_heights)
                )
                self.assertLessEqual(total_height, height + 0.01)

    def test_layout_has_seven_columns(self):
        layout = calculate_layout(1240, 430, 6)
        self.assertEqual(len(layout.widths), 7)
        self.assertTrue(all(width > 0 for width in layout.widths))
        self.assertEqual(layout.body_font_size, 7)

    def test_full_screen_layout_uses_readable_body_font(self):
        layout = calculate_layout(1880, 715, 6, (6, 5, 3, 6, 3, 6))
        self.assertEqual(layout.body_font_size, 10)

    def test_busy_schools_receive_more_height_without_changing_font(self):
        layout = calculate_layout(1880, 715, 6, (6, 5, 3, 6, 3, 6))
        self.assertGreater(layout.row_heights[5], layout.row_heights[4])
        self.assertEqual(layout.row_heights[5], layout.row_heights[0])


if __name__ == "__main__":
    unittest.main()
