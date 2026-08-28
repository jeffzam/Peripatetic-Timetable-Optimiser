import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from peripatetic_timetable.config import BASELINE_FILE, DAYS
from peripatetic_timetable.domain import TeacherLock, Timetable, WeeklyRule, normalise
from peripatetic_timetable.reports import coverage_report
from peripatetic_timetable.repository import BASELINE_SNAPSHOT_ID, TimetableRepository

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
        self.assertNotIn("PE", {item.subject for item in self.timetable.assignments})
        self.assertEqual(self.timetable.subjects_for_teacher("Rebecca Bonello"), ("PE/RSP",))

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

    def test_repository_standardises_legacy_pe_labels(self):
        with TemporaryDirectory() as directory:
            legacy = self.timetable.clone()
            legacy.assignments_for(teacher="Rebecca Bonello")[0].subject = "PE"
            legacy.change_log = [entry for entry in legacy.change_log if entry.version != "1.2"]
            repository = TimetableRepository(Path(directory) / "working.json", BASELINE_FILE)
            repository.save(legacy)
            restored = repository.load()
            self.assertEqual(restored.subjects_for_teacher("Rebecca Bonello"), ("PE/RSP",))
            self.assertTrue(any(entry.version == "1.2" for entry in restored.change_log))

    def test_repository_saves_and_restores_dated_snapshots(self):
        with TemporaryDirectory() as directory:
            repository = TimetableRepository(Path(directory) / "working.json", BASELINE_FILE)
            snapshot = repository.save_snapshot(self.timetable, "T1 approved transfer plan")
            changed = self.timetable.clone()
            changed.assignments_for(teacher="Rebecca Bonello", day="Monday")[0].school = "Dingli"
            restored = repository.load_snapshot(snapshot.snapshot_id)
            self.assertEqual(restored.current_school("Rebecca Bonello", "Monday"), "Attard")
            self.assertEqual(repository.list_snapshots()[0].label, "T1 approved transfer plan")

    def test_baseline_is_available_as_a_virtual_snapshot(self):
        with TemporaryDirectory() as directory:
            repository = TimetableRepository(Path(directory) / "working.json", BASELINE_FILE)
            restored = repository.load_snapshot(BASELINE_SNAPSHOT_ID)
            self.assertEqual(restored.to_dict(), self.timetable.to_dict())

    def test_rename_teacher_updates_placements_and_rules(self):
        self.timetable.locks.append(TeacherLock("Rebecca Bonello", "Monday", "Attard"))
        self.timetable.weekly_rules.append(WeeklyRule("Rebecca Bonello", "Attard", "EXACT", 5))
        changed = self.timetable.rename_teacher("Rebecca Bonello", "Rebecca Example")
        self.assertEqual(changed, 5)
        self.assertNotIn("Rebecca Bonello", self.timetable.teachers)
        self.assertIn("Rebecca Example", self.timetable.teachers)
        self.assertEqual(self.timetable.locks[0].teacher, "Rebecca Example")
        self.assertEqual(self.timetable.weekly_rules[0].teacher, "Rebecca Example")

    def test_remove_teacher_clears_placements_and_rules(self):
        self.timetable.locks.append(TeacherLock("Rebecca Bonello", "Monday", "Attard"))
        self.timetable.weekly_rules.append(WeeklyRule("Rebecca Bonello", "Attard", "EXACT", 5))
        removed = self.timetable.remove_teacher("Rebecca Bonello")
        self.assertEqual(removed, 5)
        self.assertNotIn("Rebecca Bonello", self.timetable.teachers)
        self.assertFalse(self.timetable.locks)
        self.assertFalse(self.timetable.weekly_rules)

    def test_add_teacher_increases_staff_without_replacing_anyone(self):
        original_teachers = set(self.timetable.teachers)
        placements = {day: "Attard" for day in DAYS}
        added = self.timetable.add_teacher("Jane Example", "Art", placements)
        self.assertEqual(added, 5)
        self.assertEqual(set(self.timetable.teachers), original_teachers | {"Jane Example"})
        assignments = self.timetable.assignments_for(teacher="Jane Example")
        self.assertEqual(len(assignments), 5)
        self.assertEqual({item.day for item in assignments}, set(DAYS))
        self.assertEqual({item.school for item in assignments}, {"Attard"})
        self.assertEqual({item.subject for item in assignments}, {"Art"})
        self.assertTrue(all(not item.baseline for item in assignments))
        self.assertEqual(self.timetable.assignment_conflicts(), {})
        coverage = next(
            item for item in coverage_report(self.timetable) if item.teacher == "Jane Example"
        )
        self.assertEqual(coverage.status, "Complete")
        self.assertEqual(coverage.missing_days, ())

    def test_add_teacher_accepts_a_different_school_each_day(self):
        placements = dict(zip(DAYS, self.timetable.school_names[:5]))
        self.timetable.add_teacher("John Example", "Music", placements)
        self.assertEqual(
            [self.timetable.current_school("John Example", day) for day in DAYS],
            list(self.timetable.school_names[:5]),
        )

    def test_add_teacher_requires_a_complete_week_and_is_atomic(self):
        original = self.timetable.to_dict()
        with self.assertRaisesRegex(ValueError, "Friday"):
            self.timetable.add_teacher(
                "Jane Example",
                "Art",
                {day: "Attard" for day in DAYS if day != "Friday"},
            )
        self.assertEqual(self.timetable.to_dict(), original)

    def test_add_teacher_rejects_duplicate_name(self):
        with self.assertRaisesRegex(ValueError, "already an active teacher"):
            self.timetable.add_teacher(
                "rebecca bonello",
                "Art",
                {day: "Attard" for day in DAYS},
            )

    def test_add_teacher_standardises_pe_label(self):
        self.timetable.add_teacher(
            "Peter Example",
            "PE",
            {day: "Rabat" for day in DAYS},
        )
        self.assertEqual(self.timetable.subjects_for_teacher("Peter Example"), ("PE/RSP",))

if __name__ == "__main__":
    unittest.main()
