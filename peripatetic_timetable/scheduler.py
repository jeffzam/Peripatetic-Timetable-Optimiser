import copy

from .config import DAYS
from .models import BatchResult, Change, RebalanceRequest

def normalise(value: str) -> str:
    return (value or "").strip().casefold().replace("ġ", "g").replace("għ", "gh")

def subjects_compatible(first: str, second: str) -> bool:
    return first == second or {first, second}.issubset({"PE", "PE/RSP"})

class RebalanceEngine:
    def __init__(self, data: dict):
        self.data = data

    def current_school(self, teacher: str, day: str, data: dict | None = None) -> str:
        source = data or self.data
        schools = {item["school"] for item in source["assignments"]
                   if normalise(item["teacher"]) == normalise(teacher) and item["day"] == day}
        if len(schools) == 1:
            return next(iter(schools))
        if len(schools) > 1:
            return "MULTIPLE: " + ", ".join(sorted(schools))
        return ""

    def _is_locked(self, teacher: str, day: str, school: str, data: dict) -> bool:
        return any(normalise(row.get("teacher", "")) == normalise(teacher)
                   and row.get("day") == day
                   and normalise(row.get("school", "")) == normalise(school)
                   for row in data.get("locks", []))

    def _is_restricted(self, teacher: str, school: str, day: str, data: dict,
                       extra: tuple[str, ...] = ()) -> bool:
        if normalise(school) in {normalise(value) for value in extra}:
            return True
        for row in data.get("teacher_restrictions", []):
            if normalise(row.get("teacher", "")) != normalise(teacher):
                continue
            if normalise(row.get("school", "")) != normalise(school):
                continue
            days = row.get("days", "ALL")
            if days == "ALL" or day in {value.strip() for value in days.split(",")}:
                return True
        return False

    @staticmethod
    def _weekly_rules_hold(data: dict) -> bool:
        for rule in data.get("weekly_rules", []):
            count = len({item["day"] for item in data["assignments"]
                         if normalise(item["teacher"]) == normalise(rule["teacher"])
                         and normalise(item["school"]) == normalise(rule["school"])})
            limit, kind = int(rule["times"]), rule["type"]
            if kind == "EXACT" and count != limit:
                return False
            if kind == "MIN" and count < limit:
                return False
            if kind == "MAX" and count > limit:
                return False
        return True

    @staticmethod
    def _swap(data: dict, teacher: str, day: str, source: str,
              target: str, swap_teacher: str) -> dict:
        result = copy.deepcopy(data)
        for item in result["assignments"]:
            if (normalise(item["teacher"]) == normalise(teacher) and item["day"] == day
                    and normalise(item["school"]) == normalise(source)):
                item["school"], item["baseline"] = target, False
            elif (normalise(item["teacher"]) == normalise(swap_teacher) and item["day"] == day
                  and normalise(item["school"]) == normalise(target)):
                item["school"], item["baseline"] = source, False
        return result

    def solve_one(self, request: RebalanceRequest, data: dict,
                  number: int) -> tuple[dict | None, Change | None, str]:
        teacher, day = request.teacher, request.day
        if day not in DAYS:
            return None, None, f"Unknown day: {day}."
        source = self.current_school(teacher, day, data)
        if not source:
            return None, None, f"{teacher} is not assigned on {day}."
        if source.startswith("MULTIPLE:"):
            return None, None, f"{teacher} appears in multiple schools on {day}."
        if self._is_locked(teacher, day, source, data):
            return None, None, f"{teacher} is locked at {source} on {day}."
        subjects = {item["subject"] for item in data["assignments"]
                    if normalise(item["teacher"]) == normalise(teacher)
                    and item["day"] == day and normalise(item["school"]) == normalise(source)}
        for target in [school["name"] for school in data["schools"]]:
            if normalise(target) == normalise(source):
                continue
            if self._is_restricted(teacher, target, day, data, request.excluded_schools):
                continue
            candidates = sorted({item["teacher"] for item in data["assignments"]
                                 if item["day"] == day
                                 and normalise(item["school"]) == normalise(target)
                                 and normalise(item["teacher"]) != normalise(teacher)
                                 and any(subjects_compatible(item["subject"], subject)
                                         for subject in subjects)})
            for candidate in candidates:
                if self._is_locked(candidate, day, target, data):
                    continue
                if self._is_restricted(candidate, source, day, data):
                    continue
                preview = self._swap(data, teacher, day, source, target, candidate)
                if not self._weekly_rules_hold(preview):
                    continue
                change = Change(number, teacher, day, source, target, candidate)
                return preview, change, change.note
        return None, None, "No compatible same-day replacement found."

    def solve_batch(self, requests: list[RebalanceRequest]) -> BatchResult:
        working, changes = copy.deepcopy(self.data), []
        for number, request in enumerate(requests, 1):
            preview, change, error = self.solve_one(request, working, number)
            if preview is None:
                return BatchResult(None, tuple(changes), f"Request {number}: {error}")
            working = preview
            changes.append(change)
        return BatchResult(working, tuple(changes))
