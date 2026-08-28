"""Core timetable entities.

This module contains data only.  It deliberately has no GUI or optimisation
dependencies so that timetable rules can be tested independently.
"""

from __future__ import annotations

import copy
import unicodedata
from dataclasses import asdict, dataclass, field, replace
from typing import Iterable

from .config import DAYS


def normalise(value: str) -> str:
    """Return an accent-insensitive key used for safe name comparisons."""
    text = (value or "").strip().casefold().translate(str.maketrans({"ħ": "h", "Ħ": "h"}))
    text = unicodedata.normalize("NFKD", text)
    return "".join(character for character in text if not unicodedata.combining(character))


@dataclass(frozen=True)
class ProjectInfo:
    title: str = "Peripatetic Teachers' Timetable"
    school_year: str = "2026/2027"
    source: str = ""
    source_date: str = ""


@dataclass(frozen=True)
class School:
    name: str
    classes: int
    breakdown: str = ""


@dataclass
class Assignment:
    school: str
    day: str
    subject: str
    teacher: str
    baseline: bool = True


@dataclass(frozen=True)
class TeacherRestriction:
    teacher: str
    school: str
    days: tuple[str, ...] = DAYS
    reason: str = ""

    def applies_on(self, day: str) -> bool:
        return day in self.days


@dataclass(frozen=True)
class TeacherLock:
    teacher: str
    day: str
    school: str


@dataclass(frozen=True)
class WeeklyRule:
    teacher: str
    school: str
    kind: str
    times: int


@dataclass(frozen=True)
class StaffNote:
    name: str
    status: str
    note: str = ""


@dataclass(frozen=True)
class ChangeLogEntry:
    version: str
    note: str


@dataclass
class Timetable:
    schools: list[School]
    assignments: list[Assignment]
    project: ProjectInfo = field(default_factory=ProjectInfo)
    restrictions: list[TeacherRestriction] = field(default_factory=list)
    locks: list[TeacherLock] = field(default_factory=list)
    weekly_rules: list[WeeklyRule] = field(default_factory=list)
    staff_notes: list[StaffNote] = field(default_factory=list)
    change_log: list[ChangeLogEntry] = field(default_factory=list)

    def clone(self) -> "Timetable":
        return copy.deepcopy(self)

    @property
    def teachers(self) -> list[str]:
        return sorted({item.teacher for item in self.assignments}, key=str.casefold)

    @property
    def school_names(self) -> list[str]:
        return [school.name for school in self.schools]

    def subjects_for_teacher(self, teacher: str) -> tuple[str, ...]:
        """Return the subjects taught by a teacher in a stable display order."""
        return tuple(
            sorted(
                {item.subject for item in self.assignments_for(teacher=teacher)},
                key=str.casefold,
            )
        )

    def rename_teacher(self, current_name: str, new_name: str) -> int:
        """Rename a teacher consistently across placements, rules, locks, and notes."""
        current_key = normalise(current_name)
        clean_name = new_name.strip()
        changed = 0
        for assignment in self.assignments:
            if normalise(assignment.teacher) == current_key:
                assignment.teacher = clean_name
                changed += 1
        self.restrictions = [
            replace(item, teacher=clean_name)
            if normalise(item.teacher) == current_key
            else item
            for item in self.restrictions
        ]
        self.locks = [
            replace(item, teacher=clean_name)
            if normalise(item.teacher) == current_key
            else item
            for item in self.locks
        ]
        self.weekly_rules = [
            replace(item, teacher=clean_name)
            if normalise(item.teacher) == current_key
            else item
            for item in self.weekly_rules
        ]
        self.staff_notes = [
            replace(item, name=clean_name)
            if normalise(item.name) == current_key
            else item
            for item in self.staff_notes
        ]
        return changed

    def add_teacher(
        self,
        teacher: str,
        subject: str,
        placements: dict[str, str],
    ) -> int:
        """Add a new teacher and one school placement for every weekday."""
        clean_name = teacher.strip()
        clean_subject = subject.strip()
        if not clean_name:
            raise ValueError("Enter the new teacher's full name.")
        if any(normalise(item) == normalise(clean_name) for item in self.teachers):
            raise ValueError(f"{clean_name} is already an active teacher.")
        if not clean_subject:
            raise ValueError("Choose the new teacher's subject.")

        missing_days = [day for day in DAYS if not placements.get(day, "").strip()]
        if missing_days:
            raise ValueError(
                "Choose a school for every weekday. Missing: " + ", ".join(missing_days) + "."
            )

        canonical_subject = (
            "PE/RSP" if normalise(clean_subject) in {"pe", "pe/rsp"} else clean_subject
        )
        new_assignments: list[Assignment] = []
        for day in DAYS:
            selected_school = self.school(placements[day])
            if selected_school is None:
                raise ValueError(f"Unknown school '{placements[day]}' for {day}.")
            new_assignments.append(
                Assignment(
                    school=selected_school.name,
                    day=day,
                    subject=canonical_subject,
                    teacher=clean_name,
                    baseline=False,
                )
            )

        self.assignments.extend(new_assignments)
        return len(new_assignments)

    def remove_teacher(self, teacher: str) -> int:
        """Remove a departed teacher's placements and teacher-specific rules."""
        teacher_key = normalise(teacher)
        previous_count = len(self.assignments)
        self.assignments = [
            item for item in self.assignments if normalise(item.teacher) != teacher_key
        ]
        self.restrictions = [
            item for item in self.restrictions if normalise(item.teacher) != teacher_key
        ]
        self.locks = [item for item in self.locks if normalise(item.teacher) != teacher_key]
        self.weekly_rules = [
            item for item in self.weekly_rules if normalise(item.teacher) != teacher_key
        ]
        return previous_count - len(self.assignments)

    def school(self, name: str) -> School | None:
        key = normalise(name)
        return next((school for school in self.schools if normalise(school.name) == key), None)

    def assignments_for(
        self,
        *,
        teacher: str | None = None,
        day: str | None = None,
        school: str | None = None,
        subject: str | None = None,
    ) -> list[Assignment]:
        teacher_key = normalise(teacher) if teacher is not None else None
        school_key = normalise(school) if school is not None else None
        subject_key = normalise(subject) if subject is not None else None
        return [
            item
            for item in self.assignments
            if (teacher_key is None or normalise(item.teacher) == teacher_key)
            and (day is None or item.day == day)
            and (school_key is None or normalise(item.school) == school_key)
            and (subject_key is None or normalise(item.subject) == subject_key)
        ]

    def schools_for_teacher(self, teacher: str, day: str) -> tuple[str, ...]:
        return tuple(sorted({item.school for item in self.assignments_for(teacher=teacher, day=day)}))

    def current_school(self, teacher: str, day: str) -> str | None:
        schools = self.schools_for_teacher(teacher, day)
        return schools[0] if len(schools) == 1 else None

    def days_at_school(self, teacher: str, school: str) -> tuple[str, ...]:
        visits = {item.day for item in self.assignments_for(teacher=teacher, school=school)}
        return tuple(day for day in DAYS if day in visits)

    def teacher_visits(self, teacher: str, school: str) -> set[str]:
        return set(self.days_at_school(teacher, school))

    def is_locked(self, teacher: str, day: str, school: str) -> bool:
        return any(
            normalise(lock.teacher) == normalise(teacher)
            and lock.day == day
            and normalise(lock.school) == normalise(school)
            for lock in self.locks
        )

    def is_restricted(
        self,
        teacher: str,
        school: str,
        day: str,
        extra_schools: Iterable[str] = (),
    ) -> bool:
        excluded = {normalise(value) for value in extra_schools}
        if normalise(school) in excluded:
            return True
        return any(
            normalise(rule.teacher) == normalise(teacher)
            and normalise(rule.school) == normalise(school)
            and rule.applies_on(day)
            for rule in self.restrictions
        )

    def validate(self) -> list[str]:
        """Return structural errors; scheduling policy is audited separately."""
        errors: list[str] = []
        valid_schools = {normalise(name) for name in self.school_names}
        seen: set[tuple[str, str, str, str]] = set()
        for item in self.assignments:
            if item.day not in DAYS:
                errors.append(f"Unknown day '{item.day}' for {item.teacher}.")
            if normalise(item.school) not in valid_schools:
                errors.append(f"Unknown school '{item.school}' for {item.teacher}.")
            if not item.teacher.strip() or not item.subject.strip():
                errors.append(f"Incomplete assignment at {item.school} on {item.day}.")
            key = (
                normalise(item.school), item.day, normalise(item.subject), normalise(item.teacher)
            )
            if key in seen:
                errors.append(
                    f"Duplicate assignment for {item.teacher}, {item.subject}, "
                    f"{item.school}, {item.day}."
                )
            seen.add(key)
        return errors

    def assignment_conflicts(self) -> dict[tuple[str, str], tuple[str, ...]]:
        conflicts: dict[tuple[str, str], tuple[str, ...]] = {}
        for teacher in self.teachers:
            for day in DAYS:
                schools = self.schools_for_teacher(teacher, day)
                if len(schools) > 1:
                    conflicts[(teacher, day)] = schools
        return conflicts

    @classmethod
    def from_dict(cls, data: dict) -> "Timetable":
        restrictions: list[TeacherRestriction] = []
        for row in data.get("teacher_restrictions", []):
            raw_days = row.get("days", "ALL")
            days = DAYS if raw_days == "ALL" else tuple(
                day.strip() for day in raw_days.split(",") if day.strip() in DAYS
            )
            restrictions.append(
                TeacherRestriction(
                    teacher=row.get("teacher", ""),
                    school=row.get("school", ""),
                    days=days,
                    reason=row.get("reason", ""),
                )
            )
        timetable = cls(
            project=ProjectInfo(**data.get("project", {})),
            schools=[School(**row) for row in data.get("schools", [])],
            assignments=[Assignment(**row) for row in data.get("assignments", [])],
            restrictions=restrictions,
            locks=[TeacherLock(**row) for row in data.get("locks", [])],
            weekly_rules=[
                WeeklyRule(
                    teacher=row["teacher"],
                    school=row["school"],
                    kind=row.get("kind", row.get("type", "EXACT")),
                    times=int(row["times"]),
                )
                for row in data.get("weekly_rules", [])
            ],
            staff_notes=[StaffNote(**row) for row in data.get("staff_notes", [])],
            change_log=[ChangeLogEntry(**row) for row in data.get("change_log", [])],
        )
        canonical_schools = {normalise(school.name): school.name for school in timetable.schools}
        for assignment in timetable.assignments:
            assignment.school = canonical_schools.get(
                normalise(assignment.school), assignment.school
            )
        return timetable

    def to_dict(self) -> dict:
        restrictions = [
            {
                "teacher": rule.teacher,
                "school": rule.school,
                "days": "ALL" if tuple(rule.days) == DAYS else ",".join(rule.days),
                "reason": rule.reason,
            }
            for rule in self.restrictions
        ]
        return {
            "project": asdict(self.project),
            "schools": [asdict(item) for item in self.schools],
            "assignments": [asdict(item) for item in self.assignments],
            "teacher_restrictions": restrictions,
            "locks": [asdict(item) for item in self.locks],
            "weekly_rules": [asdict(item) for item in self.weekly_rules],
            "staff_notes": [asdict(item) for item in self.staff_notes],
            "change_log": [asdict(item) for item in self.change_log],
        }
