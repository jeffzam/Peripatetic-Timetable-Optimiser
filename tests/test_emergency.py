import unittest

from peripatetic_timetable.audit import audit_timetable
from peripatetic_timetable.config import DAYS
from peripatetic_timetable.domain import TeacherLock, TeacherRestriction
from peripatetic_timetable.emergency import EmergencyEngine
from peripatetic_timetable.optimizer import subjects_compatible
from peripatetic_timetable.repository import TimetableRepository


class EmergencyEngineTests(unittest.TestCase):
    def setUp(self):
        self.timetable = TimetableRepository().load_baseline()

    def test_unavailable_teacher_is_removed_from_complete_preview(self):
        result = EmergencyEngine(self.timetable).solve("Ruth Borg Galea")
        self.assertTrue(result.succeeded, result.error)
        self.assertNotIn("Ruth Borg Galea", result.timetable.teachers)
        self.assertEqual(tuple(change.day for change in result.changes), DAYS)
        self.assertEqual(result.timetable.assignment_conflicts(), {})

    def test_only_same_subject_colleagues_are_reassigned(self):
        result = EmergencyEngine(self.timetable).solve("Ruth Borg Galea")
        self.assertTrue(result.succeeded, result.error)
        for change in result.changes:
            if change.cover_teacher:
                subjects = self.timetable.subjects_for_teacher(change.cover_teacher)
                self.assertTrue(
                    any(subjects_compatible(change.subject, subject) for subject in subjects)
                )

    def test_reduced_cover_is_shared_across_schools(self):
        result = EmergencyEngine(self.timetable).solve("Ruth Borg Galea")
        shortage_schools = {change.shortage_school for change in result.changes}
        self.assertGreater(len(shortage_schools), 1)
        self.assertTrue(any(change.cover_teacher for change in result.changes))

    def test_locked_colleagues_are_not_moved(self):
        for teacher in self.timetable.teachers:
            if self.timetable.subjects_for_teacher(teacher) != ("Art",):
                continue
            school = self.timetable.current_school(teacher, "Monday")
            if teacher != "Ruth Borg Galea" and school:
                self.timetable.locks.append(TeacherLock(teacher, "Monday", school))
        result = EmergencyEngine(self.timetable).solve("Ruth Borg Galea")
        monday = next(change for change in result.changes if change.day == "Monday")
        self.assertEqual(monday.cover_teacher, "")

    def test_restrictions_are_respected(self):
        self.timetable.restrictions.append(
            TeacherRestriction("Alexia Vella Schembri", "Attard", DAYS, "Test")
        )
        result = EmergencyEngine(self.timetable).solve("Ruth Borg Galea")
        self.assertTrue(result.succeeded, result.error)
        self.assertFalse(
            any(
                change.cover_teacher == "Alexia Vella Schembri"
                and change.emergency_school == "Attard"
                for change in result.changes
            )
        )

    def test_pe_emergency_plan_avoids_capacity_errors_when_possible(self):
        result = EmergencyEngine(self.timetable).solve("Rebecca Bonello")
        self.assertTrue(result.succeeded, result.error)
        self.assertFalse(
            any(issue.code == "PE_RSP_CAPACITY" for issue in audit_timetable(result.timetable))
        )

    def test_unknown_teacher_is_rejected(self):
        result = EmergencyEngine(self.timetable).solve("Unknown Person")
        self.assertFalse(result.succeeded)
        self.assertIn("Unknown teacher", result.error)


if __name__ == "__main__":
    unittest.main()
