import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import BASELINE_FILE, DEFAULT_DATA_FILE
from .domain import Timetable


BASELINE_SNAPSHOT_ID = "baseline"


@dataclass(frozen=True)
class HistorySnapshot:
    snapshot_id: str
    created_at: str
    label: str

class TimetableRepository:
    """Loads and atomically saves the user's working timetable."""

    def __init__(
        self,
        working_file: Path = DEFAULT_DATA_FILE,
        baseline_file: Path = BASELINE_FILE,
        history_dir: Path | None = None,
    ):
        self.working_file = Path(working_file)
        self.baseline_file = Path(baseline_file)
        self.history_dir = Path(history_dir) if history_dir else (
            self.working_file.parent / f"{self.working_file.stem}_history"
        )

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
        migrated = False
        old_rows = timetable.assignments_for(
            teacher="Alisichia", school="Bahrija", day="Thursday", subject="PE/RSP"
        )
        corrected_rows = timetable.assignments_for(
            teacher="Alisichia", school="Bahrija", day="Wednesday", subject="PE/RSP"
        )
        if old_rows and not corrected_rows:
            for assignment in old_rows:
                assignment.day = "Wednesday"
                assignment.baseline = True
            migrated = True
        if migrated and not any(entry.version == "1.1" for entry in timetable.change_log):
            from .domain import ChangeLogEntry

            timetable.change_log.append(
                ChangeLogEntry(
                    "1.1",
                    "Corrected source reading: Alisichia serves Bahrija on Tuesday, "
                    "Wednesday and Friday, and Rabat on Monday and Thursday.",
                )
            )

        legacy_pe = [item for item in timetable.assignments if item.subject.strip() == "PE"]
        for assignment in legacy_pe:
            assignment.subject = "PE/RSP"
            assignment.baseline = True
        if legacy_pe:
            migrated = True
            if not any(entry.version == "1.2" for entry in timetable.change_log):
                from .domain import ChangeLogEntry

                timetable.change_log.append(
                    ChangeLogEntry(
                        "1.2",
                        "Standardised every physical-education assignment to the PE/RSP label.",
                    )
                )
        return migrated

    def load_baseline(self) -> Timetable:
        with self.baseline_file.open(encoding="utf-8") as handle:
            timetable = Timetable.from_dict(json.load(handle))
        self._apply_migrations(timetable)
        return timetable

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

    def save_snapshot(self, timetable: Timetable, label: str) -> HistorySnapshot:
        """Save a dated, immutable restore point for an approved timetable."""
        errors = timetable.validate()
        if errors:
            raise ValueError("Refusing to snapshot an invalid timetable:\n" + "\n".join(errors))
        now = datetime.now().astimezone()
        snapshot = HistorySnapshot(
            snapshot_id=now.strftime("%Y%m%dT%H%M%S%f"),
            created_at=now.isoformat(timespec="seconds"),
            label=label.strip() or "Approved timetable",
        )
        self.history_dir.mkdir(parents=True, exist_ok=True)
        destination = self.history_dir / f"{snapshot.snapshot_id}.json"
        temporary = destination.with_suffix(".json.tmp")
        payload = {
            "snapshot": {
                "snapshot_id": snapshot.snapshot_id,
                "created_at": snapshot.created_at,
                "label": snapshot.label,
            },
            "timetable": timetable.to_dict(),
        }
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temporary.replace(destination)
        return snapshot

    def list_snapshots(self) -> list[HistorySnapshot]:
        if not self.history_dir.exists():
            return []
        snapshots: list[HistorySnapshot] = []
        for path in self.history_dir.glob("*.json"):
            try:
                with path.open(encoding="utf-8") as handle:
                    metadata = json.load(handle)["snapshot"]
                snapshots.append(HistorySnapshot(**metadata))
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
        return sorted(snapshots, key=lambda item: item.created_at, reverse=True)

    def load_snapshot(self, snapshot_id: str) -> Timetable:
        if snapshot_id == BASELINE_SNAPSHOT_ID:
            return self.load_baseline()
        if not re.fullmatch(r"\d{8}T\d{12}", snapshot_id):
            raise ValueError("Unknown timetable history version.")
        path = self.history_dir / f"{snapshot_id}.json"
        try:
            with path.open(encoding="utf-8") as handle:
                timetable = Timetable.from_dict(json.load(handle)["timetable"])
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not load timetable history version: {exc}") from exc
        self._apply_migrations(timetable)
        errors = timetable.validate()
        if errors:
            raise ValueError("Invalid timetable history version:\n" + "\n".join(errors))
        return timetable
