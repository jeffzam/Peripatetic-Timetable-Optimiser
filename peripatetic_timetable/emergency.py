"""Emergency timetable planning for an unavailable educator."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from itertools import product

from .config import DAYS
from .domain import Timetable, normalise
from .optimizer import TransferEngine
from .policy import DEFAULT_POLICY, PE_FAMILY, SchedulingPolicy


class EmergencyReason(str, Enum):
    SICK_LEAVE = "Sick leave"
    RESIGNED = "Resigned"


@dataclass(frozen=True)
class EmergencyChange:
    day: str
    subject: str
    emergency_school: str
    cover_teacher: str = ""
    moved_from: str = ""
    rationale: str = ""

    @property
    def shortage_school(self) -> str:
        return self.moved_from or self.emergency_school

    @property
    def note(self) -> str:
        if self.cover_teacher:
            return (
                f"{self.day}: {self.cover_teacher} moves from {self.moved_from} to "
                f"{self.emergency_school}; reduced cover remains at {self.moved_from}."
            )
        return f"{self.day}: reduced cover remains at {self.emergency_school}."


@dataclass(frozen=True)
class EmergencyResult:
    timetable: Timetable | None
    unavailable_teacher: str
    changes: tuple[EmergencyChange, ...] = ()
    warnings: tuple[str, ...] = ()
    error: str = ""
    explored_plans: int = 0

    @property
    def succeeded(self) -> bool:
        return self.timetable is not None


@dataclass(frozen=True)
class _DayOption:
    day: str
    subject: str
    emergency_school: str
    cover_teacher: str = ""
    moved_from: str = ""
    local_score: int = 0
    rationale: str = ""


class EmergencyEngine:
    """Build the least-disruptive week after one educator becomes unavailable.

    Every option removes the unavailable educator. For each affected day, the
    resulting shortage can remain at the original school or a compatible
    colleague can move there, shifting the reduced cover to that colleague's
    school. The complete week is scored together so disruption is shared rather
    than repeatedly falling on one school or one colleague.
    """

    def __init__(
        self,
        timetable: Timetable,
        policy: SchedulingPolicy = DEFAULT_POLICY,
        max_plans: int = 100_000,
    ) -> None:
        self.timetable = timetable
        self.policy = policy
        self.max_plans = max_plans
        self._pe_baseline_days = {
            school.name: len(
                {
                    (item.teacher, item.day)
                    for item in timetable.assignments_for(school=school.name)
                    if item.subject in PE_FAMILY
                }
            )
            for school in timetable.schools
        }
        self._pe_required_days = {
            school.name: policy.required_pe_rsp_days(school.classes)
            for school in timetable.schools
        }

    def solve(self, teacher: str) -> EmergencyResult:
        canonical_teacher = next(
            (item for item in self.timetable.teachers if normalise(item) == normalise(teacher)),
            "",
        )
        if not canonical_teacher:
            return EmergencyResult(None, teacher, error=f"Unknown teacher: {teacher}.")

        affected = self._affected_days(canonical_teacher)
        if not affected:
            return EmergencyResult(
                None,
                canonical_teacher,
                error="The selected educator has no active timetable placements.",
            )
        subject_groups = {
            self._subject_group(subject) for _day, _school, subject in affected
        }
        if len(subject_groups) != 1:
            return EmergencyResult(
                None,
                canonical_teacher,
                error=(
                    "This educator has unrelated subjects. Create separate subject-specific "
                    "placements before generating an emergency timetable."
                ),
            )

        option_sets = [
            self._options_for_day(canonical_teacher, day, school, subject)
            for day, school, subject in affected
        ]
        combinations = 1
        for options in option_sets:
            combinations *= len(options)
        if combinations > self.max_plans:
            return EmergencyResult(
                None,
                canonical_teacher,
                error="Too many emergency alternatives were found. Narrow the timetable first.",
            )

        ranked_plans: list[tuple[tuple, tuple[_DayOption, ...]]] = []
        for selected in product(*option_sets):
            key = (
                self._plan_score(selected),
                tuple(option.cover_teacher.casefold() for option in selected),
                tuple(option.moved_from.casefold() for option in selected),
            )
            ranked_plans.append((key, selected))
        ranked_plans.sort(key=lambda item: item[0])

        best_state: Timetable | None = None
        best_options: tuple[_DayOption, ...] = ()
        explored = 0
        for _key, selected in ranked_plans:
            explored += 1
            state = self._apply(canonical_teacher, selected)
            if self._validation_errors(state):
                continue
            best_state = state
            best_options = selected
            break

        if best_state is None:
            return EmergencyResult(
                None,
                canonical_teacher,
                error=(
                    "No emergency plan can satisfy the active locks, restrictions, weekly "
                    "rules, and one-school-per-day rule."
                ),
                explored_plans=explored,
            )

        changes = tuple(
            EmergencyChange(
                day=option.day,
                subject=option.subject,
                emergency_school=option.emergency_school,
                cover_teacher=option.cover_teacher,
                moved_from=option.moved_from,
                rationale=option.rationale,
            )
            for option in best_options
        )
        warnings = self._warnings(best_state, changes)
        return EmergencyResult(
            best_state,
            canonical_teacher,
            changes,
            warnings,
            explored_plans=explored,
        )

    def _affected_days(self, teacher: str) -> tuple[tuple[str, str, str], ...]:
        result: list[tuple[str, str, str]] = []
        for day in DAYS:
            assignments = self.timetable.assignments_for(teacher=teacher, day=day)
            schools = {item.school for item in assignments}
            if not assignments:
                continue
            if len(schools) != 1:
                continue
            subjects = sorted({item.subject for item in assignments}, key=str.casefold)
            result.append((day, next(iter(schools)), subjects[0]))
        return tuple(result)

    def _options_for_day(
        self,
        unavailable_teacher: str,
        day: str,
        emergency_school: str,
        subject: str,
    ) -> tuple[_DayOption, ...]:
        school = self.timetable.school(emergency_school)
        original_compatible = self._compatible_count(
            self.timetable, emergency_school, day, subject, excluding=unavailable_teacher
        )
        options = [
            _DayOption(
                day,
                subject,
                emergency_school,
                local_score=(school.classes if school else 0) * 3
                + (120 if original_compatible == 0 else 0),
                rationale="No colleague is moved; the original school carries the reduced cover.",
            )
        ]
        seen: set[str] = set()
        for assignment in self.timetable.assignments_for(day=day):
            cover_teacher = assignment.teacher
            cover_key = normalise(cover_teacher)
            if cover_key in seen or cover_key == normalise(unavailable_teacher):
                continue
            seen.add(cover_key)
            moved_from = self.timetable.current_school(cover_teacher, day)
            if not moved_from or normalise(moved_from) == normalise(emergency_school):
                continue
            cover_subjects = set(self.timetable.subjects_for_teacher(cover_teacher))
            if not any(self.policy.subjects_compatible(subject, item) for item in cover_subjects):
                continue
            if self.timetable.is_locked(cover_teacher, day, moved_from):
                continue
            if self.timetable.is_restricted(cover_teacher, emergency_school, day):
                continue
            donor_school = self.timetable.school(moved_from)
            donor_compatible = self._compatible_count(
                self.timetable, moved_from, day, subject, excluding=cover_teacher
            )
            familiarity = bool(self.timetable.teacher_visits(cover_teacher, emergency_school))
            options.append(
                _DayOption(
                    day,
                    subject,
                    emergency_school,
                    cover_teacher,
                    moved_from,
                    local_score=(donor_school.classes if donor_school else 0) * 3
                    + (120 if donor_compatible == 0 else 0)
                    + 8
                    - (5 if familiarity else 0),
                    rationale=(
                        "Same-subject cover; "
                        + (
                            f"{cover_teacher} already serves {emergency_school}."
                            if familiarity
                            else f"{cover_teacher} is reassigned for this day only."
                        )
                    ),
                )
            )
        return tuple(options)

    def _apply(self, unavailable_teacher: str, options: tuple[_DayOption, ...]) -> Timetable:
        result = self.timetable.clone()
        result.remove_teacher(unavailable_teacher)
        for option in options:
            if not option.cover_teacher:
                continue
            for assignment in result.assignments_for(
                teacher=option.cover_teacher,
                day=option.day,
                school=option.moved_from,
            ):
                assignment.school = option.emergency_school
                assignment.baseline = False
        return result

    def _validation_errors(self, timetable: Timetable) -> list[str]:
        errors = timetable.validate()
        errors.extend(
            f"{teacher} is assigned to two schools on {day}."
            for teacher, day in timetable.assignment_conflicts()
        )
        errors.extend(TransferEngine._validation_errors(timetable, self.timetable))
        return errors

    def _plan_score(self, options: tuple[_DayOption, ...]) -> int:
        score = sum(option.local_score for option in options)
        shortage_counts = Counter(option.moved_from or option.emergency_school for option in options)
        cover_counts = Counter(option.cover_teacher for option in options if option.cover_teacher)
        score += sum(count * count * 22 for count in shortage_counts.values())
        score += sum(count * count * 9 for count in cover_counts.values())

        subject = options[0].subject
        if subject in PE_FAMILY:
            for school in self.timetable.schools:
                actual = self._pe_baseline_days[school.name] - shortage_counts[school.name]
                deficit = max(0, self._pe_required_days[school.name] - actual)
                score += deficit * 300
        return score

    def _warnings(
        self, timetable: Timetable, changes: tuple[EmergencyChange, ...]
    ) -> tuple[str, ...]:
        warnings: list[str] = []
        for change in changes:
            if self._compatible_count(
                timetable,
                change.shortage_school,
                change.day,
                change.subject,
            ) == 0:
                warnings.append(
                    f"{change.shortage_school} has no {change.subject} educator on {change.day}."
                )
        return tuple(dict.fromkeys(warnings))

    def _compatible_count(
        self,
        timetable: Timetable,
        school: str,
        day: str,
        subject: str,
        *,
        excluding: str = "",
    ) -> int:
        return len(
            {
                item.teacher
                for item in timetable.assignments_for(school=school, day=day)
                if normalise(item.teacher) != normalise(excluding)
                and self.policy.subjects_compatible(subject, item.subject)
            }
        )

    @staticmethod
    def _subject_group(subject: str) -> str:
        return "PE/RSP" if subject in PE_FAMILY else subject
