"""College scheduling policy used by audits and transfer planning."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


PE_FAMILY = frozenset({"PE", "PE/RSP"})


@dataclass(frozen=True)
class SchedulingPolicy:
    """Configurable policy for the daily teacher-allocation layer.

    PE/RSP demand is based on one 40-minute PE lesson and two 30-minute RSP
    lessons per class each week.  One educator day is conservatively treated as
    300 available teaching minutes.  The detailed class lesson grid remains a
    later layer; this application first protects sufficient educator-day cover.
    """

    pe_minutes_per_class: int = 40
    rsp_lessons_per_class: int = 2
    rsp_minutes_per_lesson: int = 30
    teaching_minutes_per_day: int = 300
    large_school_threshold: int = 15
    minimum_large_school_educators: int = 2

    @property
    def pe_rsp_minutes_per_class(self) -> int:
        return self.pe_minutes_per_class + (
            self.rsp_lessons_per_class * self.rsp_minutes_per_lesson
        )

    def required_pe_rsp_days(self, classes: int) -> int:
        return ceil(classes * self.pe_rsp_minutes_per_class / self.teaching_minutes_per_day)

    @staticmethod
    def subjects_compatible(first: str, second: str) -> bool:
        return first == second or {first, second}.issubset(PE_FAMILY)


DEFAULT_POLICY = SchedulingPolicy()
