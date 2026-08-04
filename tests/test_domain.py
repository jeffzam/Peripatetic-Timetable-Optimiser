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
        self.assertEqual(
            self.timetable.assignment_conflicts()[("Alisichia", "Thursday")],
            ("Bahrija", "Rabat"),
        )

    def test_serialisation_round_trip(self):
        restored = Timetable.from_dict(self.timetable.to_dict())
        self.assertEqual(restored.to_dict(), self.timetable.to_dict())

    def test_name_normalisation_handles_maltese_characters(self):
        self.assertEqual(normalise("Ġanni"), normalise("Ganni"))
        self.assertEqual(normalise("Għargħur"), "gharghur")

    def test_current_school_is_detected(self):
        self.assertEqual(self.timetable.current_school("Rebecca Bonello", "Monday"), "Attard")

    def test_conflict_is_visible_in_coverage_report(self):
        row = next(item for item in coverage_report(self.timetable) if item.teacher == "Alisichia")
        self.assertEqual(row.conflict_days, ("Thursday",))
        self.assertEqual(row.status, "School conflict")

    def test_repository_round_trip(self):
        with TemporaryDirectory() as directory:
            repository = TimetableRepository(Path(directory) / "working.json", BASELINE_FILE)
            repository.save(self.timetable)
            restored = repository.load()
            self.assertEqual(restored.to_dict(), self.timetable.to_dict())

if __name__ == "__main__":
    unittest.main()
