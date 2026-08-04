from dataclasses import dataclass

from .audit import issue_counts
from .config import DAYS
from .domain import Timetable

@dataclass(frozen=True)
class CoverageRow:
    teacher: str
    assigned_days: tuple[str, ...]
    missing_days: tuple[str, ...]
    schools: tuple[str, ...]
    conflict_days: tuple[str, ...]

    @property
    def status(self) -> str:
        if self.conflict_days:
            return "School conflict"
        return "Complete" if not self.missing_days else "Missing days"

def movement_matrix(timetable: Timetable) -> dict[str, dict[str, str]]:
    matrix = {teacher: {day: "" for day in DAYS} for teacher in timetable.teachers}
    for teacher in timetable.teachers:
        for day in DAYS:
            matrix[teacher][day] = ", ".join(timetable.schools_for_teacher(teacher, day))
    return matrix

def coverage_report(timetable: Timetable) -> list[CoverageRow]:
    matrix = movement_matrix(timetable)
    rows = []
    for teacher, schedule in matrix.items():
        assigned = tuple(day for day in DAYS if schedule[day])
        missing = tuple(day for day in DAYS if not schedule[day])
        schools = tuple(sorted({
            school
            for value in schedule.values()
            for school in value.split(", ")
            if school
        }))
        conflicts = tuple(day for day in DAYS if ", " in schedule[day])
        rows.append(CoverageRow(teacher, assigned, missing, schools, conflicts))
    return rows

def summary_counts(timetable: Timetable) -> dict[str, int]:
    return {
        "schools": len(timetable.schools),
        "teachers": len(timetable.teachers),
        "assignments": len(timetable.assignments),
        "coverage_issues": issue_counts(timetable)["issues"],
    }
