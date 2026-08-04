"""Explainable timetable checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import DAYS
from .domain import Timetable
from .policy import DEFAULT_POLICY, PE_FAMILY, SchedulingPolicy


class Severity(str, Enum):
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Information"


@dataclass(frozen=True)
class AuditIssue:
    severity: Severity
    code: str
    title: str
    detail: str
    teacher: str = ""
    school: str = ""
    day: str = ""


def teacher_has_full_name(name: str) -> bool:
    """Return whether a teacher name contains at least a first name and surname."""
    return len([part for part in name.strip().split() if part]) >= 2


def audit_timetable(
    timetable: Timetable, policy: SchedulingPolicy = DEFAULT_POLICY
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for error in timetable.validate():
        issues.append(AuditIssue(Severity.ERROR, "STRUCTURE", "Invalid data", error))

    for (teacher, day), schools in timetable.assignment_conflicts().items():
        issues.append(
            AuditIssue(
                Severity.ERROR,
                "DOUBLE_BOOKED",
                "Teacher is in two schools",
                f"{teacher} is assigned to {', '.join(schools)} on {day}.",
                teacher=teacher,
                day=day,
            )
        )

    for teacher in timetable.teachers:
        if not teacher_has_full_name(teacher):
            issues.append(
                AuditIssue(
                    Severity.ERROR,
                    "INCOMPLETE_TEACHER_NAME",
                    "Teacher name is incomplete",
                    f"{teacher} needs a first name and surname. Open Staff and use Rename.",
                    teacher=teacher,
                )
            )
        missing = tuple(day for day in DAYS if not timetable.schools_for_teacher(teacher, day))
        if missing:
            issues.append(
                AuditIssue(
                    Severity.WARNING,
                    "MISSING_DAY",
                    "Teacher has an unassigned day",
                    f"{teacher} has no school on {', '.join(missing)}.",
                    teacher=teacher,
                )
            )

    for school in timetable.schools:
        pe_rsp = [
            item
            for item in timetable.assignments_for(school=school.name)
            if item.subject in PE_FAMILY
        ]
        actual_days = len({(item.teacher, item.day) for item in pe_rsp})
        required_days = policy.required_pe_rsp_days(school.classes)
        if actual_days < required_days:
            issues.append(
                AuditIssue(
                    Severity.ERROR,
                    "PE_RSP_CAPACITY",
                    "PE/RSP staffing is below demand",
                    f"{school.name} has {actual_days} educator-days; policy requires "
                    f"at least {required_days} for {school.classes} classes.",
                    school=school.name,
                )
            )
        educators = {item.teacher for item in pe_rsp}
        if (
            school.classes >= policy.large_school_threshold
            and len(educators) < policy.minimum_large_school_educators
        ):
            issues.append(
                AuditIssue(
                    Severity.WARNING,
                    "PE_RSP_RESILIENCE",
                    "Large school depends on too few PE/RSP educators",
                    f"{school.name} has {len(educators)} PE/RSP educator; policy target is "
                    f"{policy.minimum_large_school_educators}.",
                    school=school.name,
                )
            )
    return issues


def issue_counts(timetable: Timetable) -> dict[str, int]:
    issues = audit_timetable(timetable)
    return {
        "errors": sum(item.severity == Severity.ERROR for item in issues),
        "warnings": sum(item.severity == Severity.WARNING for item in issues),
        "issues": len(issues),
    }
