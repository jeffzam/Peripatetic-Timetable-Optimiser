import copy
import json
from pathlib import Path

from .config import BASELINE_FILE, DEFAULT_DATA_FILE

LIST_FIELDS = ("locks", "teacher_restrictions", "weekly_rules", "change_log")

def load_baseline() -> dict:
    with BASELINE_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)

class TimetableStore:
    def __init__(self, path: Path = DEFAULT_DATA_FILE):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return load_baseline()
        try:
            with self.path.open(encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("The timetable file must contain a JSON object")
            for field in LIST_FIELDS:
                data.setdefault(field, [])
            data.setdefault("schools", [])
            data.setdefault("assignments", [])
            return data
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not load {self.path}: {exc}") from exc

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, ensure_ascii=False)
        temporary.replace(self.path)

    def restore_baseline(self) -> None:
        self.data = copy.deepcopy(load_baseline())
        self.save()
