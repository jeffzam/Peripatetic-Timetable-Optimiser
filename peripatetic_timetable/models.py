"""Transfer-planning request and result models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import Timetable


class TransferType(str, Enum):
    FULL = "Full transfer"
    PARTIAL = "Partial transfer"


@dataclass(frozen=True)
class TransferRequest:
    teacher: str
    source_school: str
    transfer_type: TransferType
    days: tuple[str, ...] = ()
    preferred_school: str = ""
    excluded_schools: tuple[str, ...] = ()


@dataclass(frozen=True)
class AppliedChange:
    request_number: int
    teacher: str
    day: str
    source_school: str
    target_school: str
    swap_teacher: str
    score: int
    rationale: str

    @property
    def note(self) -> str:
        return (
            f"{self.request_number}. {self.teacher}: {self.source_school} → "
            f"{self.target_school}; {self.swap_teacher}: {self.target_school} → "
            f"{self.source_school} ({self.day})."
        )


@dataclass(frozen=True)
class TransferCandidate:
    timetable: Timetable
    change: AppliedChange


@dataclass(frozen=True)
class TransferResult:
    timetable: Timetable | None
    changes: tuple[AppliedChange, ...] = ()
    error: str = ""
    explored_states: int = 0

    @property
    def succeeded(self) -> bool:
        return self.timetable is not None
