from dataclasses import dataclass

@dataclass(frozen=True)
class RebalanceRequest:
    teacher: str
    day: str
    excluded_schools: tuple[str, ...] = ()

@dataclass(frozen=True)
class Change:
    request_number: int
    teacher: str
    day: str
    source_school: str
    target_school: str
    swap_teacher: str

    @property
    def note(self) -> str:
        return (f"{self.request_number}. {self.teacher}: {self.source_school} -> "
                f"{self.target_school} on {self.day}; {self.swap_teacher}: "
                f"{self.target_school} -> {self.source_school}.")

@dataclass(frozen=True)
class BatchResult:
    data: dict | None
    changes: tuple[Change, ...] = ()
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return self.data is not None
