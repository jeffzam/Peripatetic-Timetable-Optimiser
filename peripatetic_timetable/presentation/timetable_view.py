"""Responsive single-screen timetable grid."""

from __future__ import annotations

import re
import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk

from ..config import DAYS
from ..domain import School, Timetable
from .theme import COLORS


SUBJECT_COLORS = {
    "Art": "#A13B72",
    "Music": "#365F9D",
    "PE/RSP": "#25714F",
    "PSCD": "#A95714",
}


@dataclass(frozen=True)
class TableLayout:
    margin: float
    widths: tuple[float, ...]
    header_height: float
    row_heights: tuple[float, ...]
    body_font_size: int

    @property
    def total_width(self) -> float:
        return (self.margin * 2) + sum(self.widths)


def calculate_layout(
    width: int,
    height: int,
    school_count: int,
    row_weights: tuple[int, ...] | None = None,
) -> TableLayout:
    """Fit the complete timetable into the available viewport without scrolling."""
    margin = 2.0
    usable_width = max(1.0, width - (margin * 2))
    school_width = max(72.0, min(112.0, usable_width * 0.075))
    classes_width = max(92.0, min(132.0, usable_width * 0.09))
    day_width = max(1.0, (usable_width - school_width - classes_width) / len(DAYS))
    header_height = max(28.0, min(40.0, height * 0.075))
    body_height = max(1.0, height - (margin * 2) - header_height)
    weights = row_weights or tuple(5 for _ in range(school_count))
    if len(weights) != school_count or any(weight < 1 for weight in weights):
        raise ValueError("Row weights must contain one positive value per school.")
    total_weight = max(1, sum(weights))
    row_heights = tuple(body_height * weight / total_weight for weight in weights)
    line_budget = body_height / total_weight
    if line_budget >= 20:
        body_font_size = 10
    elif line_budget >= 18:
        body_font_size = 9
    elif line_budget >= 16:
        body_font_size = 8
    else:
        body_font_size = 7
    return TableLayout(
        margin=margin,
        widths=(school_width, classes_width, *([day_width] * len(DAYS))),
        header_height=header_height,
        row_heights=row_heights,
        body_font_size=body_font_size,
    )


class TimetableCanvas(ttk.Frame):
    """Box-style timetable that always displays the whole week and every school."""

    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._timetable: Timetable | None = None
        self._preview = False
        self.canvas.bind("<Configure>", lambda _event: self.render())

    def set_timetable(self, timetable: Timetable, preview: bool = False) -> None:
        self._timetable = timetable
        self._preview = preview
        self.render()

    def render(self) -> None:
        if self._timetable is None:
            return
        viewport_width = self.canvas.winfo_width()
        viewport_height = self.canvas.winfo_height()
        if viewport_width < 300 or viewport_height < 200:
            return

        daily_assignments = [
            [
                self._timetable.assignments_for(school=school.name, day=day)
                for day in DAYS
            ]
            for school in self._timetable.schools
        ]
        row_weights = tuple(
            max(3, *(len(assignments) for assignments in daily))
            for daily in daily_assignments
        )
        layout = calculate_layout(
            viewport_width,
            viewport_height,
            len(self._timetable.schools),
            row_weights,
        )
        self.canvas.delete("all")
        x0 = layout.margin
        y = layout.margin
        headers = ["PRIMARY SCHOOL", "CLASSES", *[day.upper() for day in DAYS]]
        x = x0
        for label, cell_width in zip(headers, layout.widths):
            self._cell(
                x,
                y,
                cell_width,
                layout.header_height,
                COLORS["navy"],
                label,
                "white",
                font_size=8,
                bold=True,
                anchor="center",
            )
            x += cell_width
        y += layout.header_height

        for school, daily, row_height in zip(
            self._timetable.schools,
            daily_assignments,
            layout.row_heights,
        ):
            x = x0
            self._cell(
                x,
                y,
                layout.widths[0],
                row_height,
                COLORS["blue_light"],
                school.name,
                COLORS["navy"],
                font_size=layout.body_font_size,
                bold=True,
                anchor="center",
            )
            x += layout.widths[0]
            self._cell(
                x,
                y,
                layout.widths[1],
                row_height,
                "#F7F9FB",
                self._compact_classes(school),
                COLORS["ink"],
                font_size=layout.body_font_size,
                anchor="nw",
            )
            x += layout.widths[1]
            for index, assignments in enumerate(daily):
                changed = any(not assignment.baseline for assignment in assignments)
                fill = COLORS["preview"] if self._preview and changed else "white"
                cell_width = layout.widths[index + 2]
                self._assignment_cell(
                    x,
                    y,
                    cell_width,
                    row_height,
                    fill,
                    assignments,
                    layout.body_font_size,
                )
                x += cell_width
            y += row_height

    @staticmethod
    def _compact_classes(school: School) -> str:
        values: list[str] = []
        for line in school.breakdown.splitlines():
            match = re.search(r"Yr\s*(\d+)\s*[-–]\s*(\d+)", line.strip())
            if match:
                values.append(f"Y{match.group(1)}:{match.group(2)}")
        grouped = [" · ".join(values[index : index + 3]) for index in range(0, len(values), 3)]
        return "\n".join([f"{school.classes} classes", *grouped])

    def _assignment_cell(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: str,
        assignments,
        font_size: int,
    ) -> None:
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill=fill,
            outline=COLORS["line"],
            width=1,
        )
        if not assignments:
            return
        font_spec = ("Segoe UI", font_size)
        measured_font = tkfont.Font(family="Segoe UI", size=font_size)
        line_height = measured_font.metrics("linespace")
        content_height = line_height * len(assignments)
        top = y + max(2.0, (height - content_height) / 2)
        for index, assignment in enumerate(assignments):
            self.canvas.create_text(
                x + 6,
                top + (index * line_height),
                text=f"{assignment.subject} — {assignment.teacher}",
                anchor="nw",
                fill=SUBJECT_COLORS.get(assignment.subject, COLORS["ink"]),
                font=font_spec,
            )

    def _cell(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        fill: str,
        text: str,
        colour: str,
        *,
        font_size: int,
        bold: bool = False,
        anchor: str,
    ) -> None:
        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill=fill,
            outline=COLORS["line"],
            width=1,
        )
        centered = anchor == "center"
        padding = 3 if font_size <= 7 else 5
        self.canvas.create_text(
            x + width / 2 if centered else x + padding,
            y + height / 2 if centered else y + padding,
            text=text,
            anchor="center" if centered else "nw",
            width=max(1, width - (padding * 2)),
            fill=colour,
            font=("Segoe UI", font_size, "bold" if bold else "normal"),
        )
