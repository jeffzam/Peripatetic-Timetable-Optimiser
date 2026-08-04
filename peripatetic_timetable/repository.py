import json
import shutil
from pathlib import Path

from .config import BASELINE_FILE, DEFAULT_DATA_FILE
from .domain import Timetable

class TimetableRepository:
    """Loads and atomically saves the user's working timetable."""

    def __init__(self, working_file: Path = DEFAULT_DATA_FILE, baseline_file: Path = BASELINE_FILE):
        self.working_file = Path(working_file)
        self.baseline_file = Path(baseline_file)

    def load(self) -> Timetable:
        source = self.working_file if self.working_file.exists() else self.baseline_file
        try:
            with source.open(encoding="utf-8") as handle:
                timetable = Timetable.from_dict(json.load(handle))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not load timetable data from {source}: {exc}") from exc
        errors = timetable.validate()
        if errors:
            raise ValueError("Invalid timetable data:\n" + "\n".join(errors))
        migrated = self._apply_migrations(timetable)
        if migrated and source == self.working_file:
            self.save(timetable)
        return timetable

    @staticmethod
    def _apply_migrations(timetable: Timetable) -> bool:
        """Apply narrow, evidence-backed corrections to older working copies."""
        old_rows = timetable.assignments_for(
            teacher="Alisichia", school="Bahrija", day="Thursday", subject="PE/RSP"
        )
        corrected_rows = timetable.assignments_for(
            teacher="Alisichia", school="Bahrija", day="Wednesday", subject="PE/RSP"
        )
        if not old_rows or corrected_rows:
            return False
        for assignment in old_rows:
            assignment.day = "Wednesday"
            assignment.baseline = True
        if not any(entry.version == "1.1" for entry in timetable.change_log):
            from .domain import ChangeLogEntry

            timetable.change_log.append(
                ChangeLogEntry(
                    "1.1",
                    "Corrected source reading: Alisichia serves Bahrija on Tuesday, "
                    "Wednesday and Friday, and Rabat on Monday and Thursday.",
                )
            )
        return True

    def load_baseline(self) -> Timetable:
        with self.baseline_file.open(encoding="utf-8") as handle:
            return Timetable.from_dict(json.load(handle))

    def save(self, timetable: Timetable) -> None:
        errors = timetable.validate()
        if errors:
            raise ValueError("Refusing to save an invalid timetable:\n" + "\n".join(errors))
        self.working_file.parent.mkdir(parents=True, exist_ok=True)
        backup = self.working_file.with_suffix(self.working_file.suffix + ".bak")
        if self.working_file.exists():
            shutil.copy2(self.working_file, backup)
        temporary = self.working_file.with_suffix(self.working_file.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(timetable.to_dict(), handle, ensure_ascii=False, indent=2)
        temporary.replace(self.working_file)

    def restore_baseline(self) -> Timetable:
        timetable = self.load_baseline()
        self.save(timetable)
        return timetable
