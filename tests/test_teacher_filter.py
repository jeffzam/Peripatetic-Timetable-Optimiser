import unittest

from peripatetic_timetable.presentation.rebalance_tab import teacher_label


class TeacherFilterTests(unittest.TestCase):
    def test_teacher_label_includes_subject(self):
        self.assertEqual(teacher_label("Rebecca Bonello", ("PE",)), "Rebecca Bonello (PE)")

    def test_teacher_label_handles_multiple_subjects(self):
        self.assertEqual(
            teacher_label("Example Teacher", ("Art", "Music")),
            "Example Teacher (Art / Music)",
        )


if __name__ == "__main__":
    unittest.main()
