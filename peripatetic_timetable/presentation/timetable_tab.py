from tkinter import ttk

from ..domain import Timetable
from ..reports import summary_counts
from .theme import COLORS
from .timetable_view import TimetableCanvas

class TimetableTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="App.TFrame")
        self.metrics = {}
        self._build()

    def _build(self):
        top = ttk.Frame(self, style="App.TFrame")
        top.pack(fill="x", padx=8, pady=(8, 5))
        for key, title in (
            ("schools", "Schools"), ("teachers", "Teachers"),
            ("assignments", "Assignments"), ("coverage_issues", "Audit issues"),
        ):
            card = ttk.Frame(top, style="Card.TFrame", padding=(14, 9))
            card.pack(side="left", padx=(0, 8))
            value = ttk.Label(card, text="0", style="Metric.TLabel")
            value.pack(side="left")
            ttk.Label(card, text=title, style="Muted.TLabel").pack(side="left", padx=(8, 0))
            self.metrics[key] = value
        self.mode = ttk.Label(top, text="SAVED TIMETABLE", background=COLORS["green"], foreground="white", padding=(12, 6), font=("Segoe UI", 9, "bold"))
        self.mode.pack(side="right")
        self.canvas = TimetableCanvas(self)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def show(self, timetable: Timetable, preview: bool = False) -> None:
        for key, value in summary_counts(timetable).items():
            self.metrics[key].configure(text=str(value))
        self.mode.configure(
            text="PREVIEW — NOT YET SAVED" if preview else "SAVED TIMETABLE",
            background=COLORS["orange"] if preview else COLORS["green"],
        )
        self.canvas.set_timetable(timetable, preview)
