"""Constraint-safe full and partial transfer planning."""

from __future__ import annotations

from .config import DAYS
from .domain import Timetable, normalise
from .models import (
    AppliedChange,
    TransferCandidate,
    TransferRequest,
    TransferResult,
    TransferType,
)
from .policy import DEFAULT_POLICY, SchedulingPolicy


def subjects_compatible(first: str, second: str) -> bool:
    """Compatibility helper retained as the public policy entry point."""
    return DEFAULT_POLICY.subjects_compatible(first, second)


class TransferEngine:
    """Find low-disruption swaps for full or partial transfer requests.

    A full transfer moves every day the requesting teacher currently works at
    the selected source school to one destination school.  A partial transfer
    moves only the selected days.  Different counterpart teachers may cover the
    source on different days, but the requesting teacher has one destination for
    the complete request.
    """

    def __init__(
        self,
        timetable: Timetable,
        policy: SchedulingPolicy = DEFAULT_POLICY,
        max_states: int = 5_000,
    ) -> None:
        self.timetable = timetable
        self.policy = policy
        self.max_states = max_states
        self._explored = 0

    def solve(self, requests: list[TransferRequest]) -> TransferResult:
        if not requests:
            return TransferResult(None, error="Add at least one transfer request first.")
        self._explored = 0
        result = self._solve_requests(self.timetable.clone(), requests, 0, ())
        if result is not None:
            timetable, changes = result
            return TransferResult(
                timetable=timetable,
                changes=changes,
                explored_states=self._explored,
            )
        error = (
            "The search limit was reached. Narrow the destination schools or split the batch."
            if self._explored >= self.max_states
            else "No complete transfer plan satisfies the active locks, restrictions, "
            "weekly rules, subject cover, and one-school-per-day rule."
        )
        return TransferResult(None, error=error, explored_states=self._explored)

    def _solve_requests(
        self,
        state: Timetable,
        requests: list[TransferRequest],
        request_index: int,
        changes: tuple[AppliedChange, ...],
    ) -> tuple[Timetable, tuple[AppliedChange, ...]] | None:
        if request_index == len(requests):
            return state, changes
        if self._explored >= self.max_states:
            return None

        request = requests[request_index]
        days, error = self._request_days(state, request)
        if error:
            return None
        targets = self._target_schools(state, request)
        for target in targets:
            result = self._solve_request_days(
                state,
                request,
                days,
                target,
                request_index + 1,
                0,
                (),
            )
            if result is None:
                continue
            next_state, request_changes = result
            completed = self._solve_requests(
                next_state,
                requests,
                request_index + 1,
                changes + request_changes,
            )
            if completed is not None:
                return completed
        return None

    def _solve_request_days(
        self,
        state: Timetable,
        request: TransferRequest,
        days: tuple[str, ...],
        target: str,
        request_number: int,
        day_index: int,
        changes: tuple[AppliedChange, ...],
    ) -> tuple[Timetable, tuple[AppliedChange, ...]] | None:
        if day_index == len(days):
            return state, changes
        if self._explored >= self.max_states:
            return None
        candidates = self.find_day_candidates(
            state,
            request=request,
            day=days[day_index],
            target=target,
            request_number=request_number,
        )
        for candidate in candidates:
            self._explored += 1
            result = self._solve_request_days(
                candidate.timetable,
                request,
                days,
                target,
                request_number,
                day_index + 1,
                changes + (candidate.change,),
            )
            if result is not None:
                return result
        return None

    def find_day_candidates(
        self,
        timetable: Timetable,
        *,
        request: TransferRequest,
        day: str,
        target: str,
        request_number: int = 1,
    ) -> list[TransferCandidate]:
        source = request.source_school
        if day not in DAYS:
            return []
        source_assignments = timetable.assignments_for(
            teacher=request.teacher, day=day, school=source
        )
        if not source_assignments:
            return []
        if len(timetable.schools_for_teacher(request.teacher, day)) != 1:
            return []
        if timetable.is_locked(request.teacher, day, source):
            return []
        if timetable.is_restricted(request.teacher, target, day, request.excluded_schools):
            return []

        source_subjects = {item.subject for item in source_assignments}
        candidates: list[TransferCandidate] = []
        seen: set[str] = set()
        for assignment in timetable.assignments_for(day=day, school=target):
            swap_teacher = assignment.teacher
            swap_key = normalise(swap_teacher)
            if swap_key in seen or swap_key == normalise(request.teacher):
                continue
            seen.add(swap_key)
            counterpart = timetable.assignments_for(
                teacher=swap_teacher, day=day, school=target
            )
            counterpart_subjects = {item.subject for item in counterpart}
            if not self._subject_sets_compatible(source_subjects, counterpart_subjects):
                continue
            if len(timetable.schools_for_teacher(swap_teacher, day)) != 1:
                continue
            if timetable.is_locked(swap_teacher, day, target):
                continue
            if timetable.is_restricted(swap_teacher, source, day):
                continue

            preview = self._apply_swap(
                timetable, request.teacher, swap_teacher, day, source, target
            )
            if self._validation_errors(preview, timetable):
                continue
            score, rationale = self._score(
                timetable,
                request.teacher,
                swap_teacher,
                source,
                target,
                source_subjects,
                counterpart_subjects,
            )
            candidates.append(
                TransferCandidate(
                    preview,
                    AppliedChange(
                        request_number=request_number,
                        teacher=request.teacher,
                        day=day,
                        source_school=source,
                        target_school=target,
                        swap_teacher=swap_teacher,
                        score=score,
                        rationale=rationale,
                    ),
                )
            )
        candidates.sort(
            key=lambda item: (
                item.change.score,
                item.change.swap_teacher.casefold(),
            )
        )
        return candidates

    @staticmethod
    def _request_days(
        timetable: Timetable, request: TransferRequest
    ) -> tuple[tuple[str, ...], str]:
        if request.teacher not in timetable.teachers:
            return (), f"Unknown teacher: {request.teacher}."
        if timetable.school(request.source_school) is None:
            return (), f"Unknown source school: {request.source_school}."
        if request.transfer_type == TransferType.FULL:
            days = timetable.days_at_school(request.teacher, request.source_school)
        else:
            days = tuple(day for day in DAYS if day in request.days)
        if not days:
            return (), "The request does not contain any assigned days."
        if any(
            request.source_school not in timetable.schools_for_teacher(request.teacher, day)
            for day in days
        ):
            return (), "One or more selected days are not at the source school."
        return days, ""

    @staticmethod
    def _target_schools(timetable: Timetable, request: TransferRequest) -> tuple[str, ...]:
        excluded = {normalise(item) for item in request.excluded_schools}
        if request.preferred_school:
            candidates = (request.preferred_school,)
        else:
            candidates = tuple(timetable.school_names)
        return tuple(
            school
            for school in candidates
            if normalise(school) != normalise(request.source_school)
            and normalise(school) not in excluded
        )

    def _subject_sets_compatible(self, first: set[str], second: set[str]) -> bool:
        return (
            bool(first)
            and bool(second)
            and all(any(self.policy.subjects_compatible(a, b) for b in second) for a in first)
            and all(any(self.policy.subjects_compatible(b, a) for a in first) for b in second)
        )

    @staticmethod
    def _apply_swap(
        timetable: Timetable,
        teacher: str,
        swap_teacher: str,
        day: str,
        source: str,
        target: str,
    ) -> Timetable:
        result = timetable.clone()
        for item in result.assignments:
            if (
                normalise(item.teacher) == normalise(teacher)
                and item.day == day
                and normalise(item.school) == normalise(source)
            ):
                item.school, item.baseline = target, False
            elif (
                normalise(item.teacher) == normalise(swap_teacher)
                and item.day == day
                and normalise(item.school) == normalise(target)
            ):
                item.school, item.baseline = source, False
        return result

    @staticmethod
    def _validation_errors(timetable: Timetable, previous: Timetable) -> list[str]:
        errors = timetable.validate()
        previous_conflicts = set(previous.assignment_conflicts())
        new_conflicts = set(timetable.assignment_conflicts()) - previous_conflicts
        for teacher, day in sorted(new_conflicts):
            errors.append(f"{teacher} would be assigned to two schools on {day}.")
        for rule in timetable.weekly_rules:
            count = len(timetable.teacher_visits(rule.teacher, rule.school))
            if rule.kind == "EXACT" and count != rule.times:
                errors.append("An exact weekly frequency rule would be broken.")
            elif rule.kind == "MIN" and count < rule.times:
                errors.append("A minimum weekly frequency rule would be broken.")
            elif rule.kind == "MAX" and count > rule.times:
                errors.append("A maximum weekly frequency rule would be broken.")
        return errors

    @staticmethod
    def _score(
        timetable: Timetable,
        teacher: str,
        swap_teacher: str,
        source: str,
        target: str,
        source_subjects: set[str],
        counterpart_subjects: set[str],
    ) -> tuple[int, str]:
        score = 0
        reasons: list[str] = []
        if source_subjects == counterpart_subjects:
            reasons.append("exact subject match")
        else:
            score += 20
            reasons.append("PE and PE/RSP are compatible")
        if timetable.teacher_visits(teacher, target):
            score -= 6
            reasons.append(f"{teacher} already knows {target}")
        else:
            score += 4
        if timetable.teacher_visits(swap_teacher, source):
            score -= 6
            reasons.append(f"{swap_teacher} already knows {source}")
        else:
            score += 4
        return score, "; ".join(reasons)


# Compatibility alias for code using the earlier class name.
RebalanceEngine = TransferEngine
