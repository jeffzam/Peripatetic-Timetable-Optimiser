import unittest

from peripatetic_timetable.domain import TeacherLock, TeacherRestriction, WeeklyRule
from peripatetic_timetable.models import TransferRequest, TransferType
from peripatetic_timetable.optimizer import TransferEngine, subjects_compatible
from peripatetic_timetable.repository import TimetableRepository


class TransferEngineTests(unittest.TestCase):
    def setUp(self):
        self.timetable = TimetableRepository().load_baseline()

    def partial(self, teacher="Rebecca Bonello", source="Attard", days=("Monday",)):
        return TransferRequest(teacher, source, TransferType.PARTIAL, days)

    def test_pe_and_pe_rsp_are_compatible(self):
        self.assertTrue(subjects_compatible("PE", "PE/RSP"))
        self.assertFalse(subjects_compatible("Art", "Music"))

    def test_partial_transfer_moves_both_teachers(self):
        result = TransferEngine(self.timetable).solve([self.partial()])
        self.assertTrue(result.succeeded, result.error)
        change = result.changes[0]
        self.assertEqual(
            result.timetable.current_school("Rebecca Bonello", "Monday"),
            change.target_school,
        )
        self.assertEqual(
            result.timetable.current_school(change.swap_teacher, "Monday"), "Attard"
        )

    def test_full_transfer_moves_every_source_day_to_one_school(self):
        request = TransferRequest(
            "Rebecca Bonello",
            "Attard",
            TransferType.FULL,
            preferred_school="Dingli",
        )
        result = TransferEngine(self.timetable).solve([request])
        self.assertTrue(result.succeeded, result.error)
        self.assertEqual(len(result.changes), 5)
        self.assertEqual({change.target_school for change in result.changes}, {"Dingli"})

    def test_preferred_destination_is_respected(self):
        request = TransferRequest(
            "Rebecca Bonello",
            "Attard",
            TransferType.PARTIAL,
            ("Monday",),
            preferred_school="Dingli",
        )
        result = TransferEngine(self.timetable).solve([request])
        self.assertTrue(result.succeeded, result.error)
        self.assertEqual(result.changes[0].target_school, "Dingli")

    def test_lock_blocks_removal(self):
        self.timetable.locks.append(TeacherLock("Rebecca Bonello", "Monday", "Attard"))
        result = TransferEngine(self.timetable).solve([self.partial()])
        self.assertFalse(result.succeeded)

    def test_day_specific_restriction(self):
        self.timetable.restrictions.append(
            TeacherRestriction("Rebecca Bonello", "Dingli", ("Monday",), "Test")
        )
        request = TransferRequest(
            "Rebecca Bonello",
            "Attard",
            TransferType.PARTIAL,
            ("Monday",),
            preferred_school="Dingli",
        )
        self.assertFalse(TransferEngine(self.timetable).solve([request]).succeeded)

    def test_weekly_rule_is_enforced(self):
        self.timetable.weekly_rules.append(
            WeeklyRule("Rebecca Bonello", "Attard", "EXACT", 5)
        )
        self.assertFalse(TransferEngine(self.timetable).solve([self.partial()]).succeeded)

    def test_empty_request_list_is_rejected(self):
        result = TransferEngine(self.timetable).solve([])
        self.assertFalse(result.succeeded)
        self.assertIn("request", result.error)


if __name__ == "__main__":
    unittest.main()
