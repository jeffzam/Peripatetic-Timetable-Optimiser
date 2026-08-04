import tkinter as tk
from tkinter import ttk

from ..config import DAYS
from ..domain import Timetable
from .theme import COLORS

class TimetableCanvas(ttk.Frame):
    """Scrollable, box-style timetable matching the working document."""

    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._timetable = None
        self._preview = False
        self.canvas.bind("<Configure>", lambda _event: self.render())

    def set_timetable(self, timetable: Timetable, preview: bool = False) -> None:
        self._timetable = timetable
        self._preview = preview
        self.render()

    def render(self) -> None:
        if self._timetable is None:
            return
        self.canvas.delete("all")
        viewport = max(self.canvas.winfo_width(), 900)
        school_width = 155
        classes_width = 155
        day_width = max(205, (viewport - school_width - classes_width - 30) / 5)
        widths = [school_width, classes_width, *([day_width] * 5)]
        total_width = sum(widths)
        x0, y = 12, 12
        heading_height = 54
        headers = ["PRIMARY SCHOOL", "CLASSES", *[day.upper() for day in DAYS]]
        x = x0
        for label, width in zip(headers, widths):
            self._cell(x, y, width, heading_height, COLORS["navy"], label, "white", True, "center")
            x += width
        y += heading_height
        for school in self._timetable.schools:
            daily = [
                self._timetable.assignments_for(school=school.name, day=day)
                for day in DAYS
            ]
            max_lines = max([6, *(len(items) * 2 for items in daily)])
            row_height = max(112, 24 + max_lines * 16)
            x = x0
            self._cell(x, y, widths[0], row_height, COLORS["blue_light"], school.name, COLORS["navy"], True, "center")
            x += widths[0]
            class_text = f"{school.classes} classes\n\n{school.breakdown}"
            self._cell(x, y, widths[1], row_height, "#F7F9FB", class_text, COLORS["ink"], False, "nw")
            x += widths[1]
            for index, items in enumerate(daily):
                text = "\n".join(f"{item.subject}  —  {item.teacher}" for item in items)
                changed = any(not item.baseline for item in items)
                fill = COLORS["preview"] if self._preview and changed else "white"
                self._cell(x, y, widths[index + 2], row_height, fill, text, COLORS["ink"], False, "nw")
                x += widths[index + 2]
            y += row_height
        self.canvas.configure(scrollregion=(0, 0, total_width + 24, y + 12))

    def _cell(self, x, y, width, height, fill, text, colour, bold, anchor):
        self.canvas.create_rectangle(x, y, x + width, y + height, fill=fill, outline=COLORS["line"], width=1)
        centered = anchor == "center"
        self.canvas.create_text(
            x + width / 2 if centered else x + 9,
            y + height / 2 if centered else y + 9,
            text=text,
            anchor="center" if centered else "nw",
            width=width - 18,
            fill=colour,
            font=("Segoe UI", 9, "bold" if bold else "normal"),
        )
