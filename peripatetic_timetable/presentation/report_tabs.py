from tkinter import ttk

from ..config import DAYS
from ..domain import Timetable
from ..reports import coverage_report, movement_matrix

class MovementTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="App.TFrame")
        self.tree = ttk.Treeview(self, columns=("teacher", *DAYS), show="headings")
        self.tree.heading("teacher", text="Teacher"); self.tree.column("teacher", width=220)
        for day in DAYS:
            self.tree.heading(day, text=day); self.tree.column(day, width=180)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

    def show(self, timetable: Timetable):
        self.tree.delete(*self.tree.get_children())
        for teacher, schedule in movement_matrix(timetable).items():
            self.tree.insert("", "end", values=(teacher, *(schedule[day] or "—" for day in DAYS)))

class CoverageTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="App.TFrame")
        self.tree = ttk.Treeview(self, columns=("teacher", "count", "assigned", "missing", "conflicts", "schools", "status"), show="headings")
        for column, label, width in (
            ("teacher", "Teacher", 220), ("count", "Days", 70), ("assigned", "Assigned days", 260),
            ("missing", "Missing days", 210), ("conflicts", "Conflict days", 150),
            ("schools", "Schools", 250), ("status", "Status", 125),
        ):
            self.tree.heading(column, text=label); self.tree.column(column, width=width)
        self.tree.tag_configure("issue", background="#FFF1F0")
        self.tree.tag_configure("complete", background="#EDF8F1")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

    def show(self, timetable: Timetable):
        self.tree.delete(*self.tree.get_children())
        for row in coverage_report(timetable):
            self.tree.insert("", "end", values=(
                row.teacher, len(row.assigned_days), ", ".join(row.assigned_days),
                ", ".join(row.missing_days) or "—", ", ".join(row.conflict_days) or "—",
                ", ".join(row.schools), row.status,
            ), tags=("issue" if row.missing_days or row.conflict_days else "complete",))

class ChangeLogTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="App.TFrame")
        self.tree = ttk.Treeview(self, columns=("version", "note"), show="headings")
        self.tree.heading("version", text="Version"); self.tree.column("version", width=110, anchor="center")
        self.tree.heading("note", text="Change"); self.tree.column("note", width=900)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)

    def show(self, timetable: Timetable):
        self.tree.delete(*self.tree.get_children())
        for item in reversed(timetable.change_log):
            self.tree.insert("", "end", values=(item.version, item.note))
