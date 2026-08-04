import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from peripatetic_timetable.config import BASELINE_FILE
from peripatetic_timetable.domain import Timetable, normalise
from peripatetic_timetable.reports import coverage_report
from peripatetic_timetable.repository import TimetableRepository

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.timetable = TimetableRepository().load_baseline()

    def test_baseline_is_valid(self):
        self.assertEqual(self.timetable.validate(), [])
        self.assertEqual(len(self.timetable.schools), 6)
        self.assertGreater(len(self.timetable.teachers), 10)
        self.assertEqual(self.timetable.assignment_conflicts(), {})
        self.assertEqual(
            self.timetable.current_school("Alisichia", "Wednesday"), "Bahrija"
        )
        self.assertEqual(
            self.timetable.current_school("Alisichia", "Thursday"), "Rabat"
        )

    def test_serialisation_round_trip(self):
        restored = Timetable.from_dict(self.timetable.to_dict())
        self.assertEqual(restored.to_dict(), self.timetable.to_dict())

    def test_name_normalisation_handles_maltese_characters(self):
        self.assertEqual(normalise("Ġanni"), normalise("Ganni"))
        self.assertEqual(normalise("Għargħur"), "gharghur")

    def test_current_school_is_detected(self):
        self.assertEqual(self.timetable.current_school("Rebecca Bonello", "Monday"), "Attard")

    def test_alisichia_has_complete_weekly_coverage(self):
        row = next(item for item in coverage_report(self.timetable) if item.teacher == "Alisichia")
        self.assertEqual(row.conflict_days, ())
        self.assertEqual(row.missing_days, ())
        self.assertEqual(row.status, "Complete")

    def test_repository_round_trip(self):
        with TemporaryDirectory() as directory:
            repository = TimetableRepository(Path(directory) / "working.json", BASELINE_FILE)
            repository.save(self.timetable)
            restored = repository.load()
            self.assertEqual(restored.to_dict(), self.timetable.to_dict())

    def test_repository_migrates_the_earlier_alisichia_reading(self):
        with TemporaryDirectory() as directory:
            legacy = self.timetable.clone()
            assignment = legacy.assignments_for(
                teacher="Alisichia", school="Bahrija", day="Wednesday", subject="PE/RSP"
            )[0]
            assignment.day = "Thursday"
            legacy.change_log = [entry for entry in legacy.change_log if entry.version != "1.1"]
            repository = TimetableRepository(Path(directory) / "working.json", BASELINE_FILE)
            repository.save(legacy)
            restored = repository.load()
            self.assertEqual(
                restored.current_school("Alisichia", "Wednesday"), "Bahrija"
            )
            self.assertEqual(restored.current_school("Alisichia", "Thursday"), "Rabat")
            self.assertTrue(any(entry.version == "1.1" for entry in restored.change_log))

if __name__ == "__main__":
    unittest.main()
