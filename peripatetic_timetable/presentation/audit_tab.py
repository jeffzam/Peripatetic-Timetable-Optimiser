"""Detailed policy audit screen."""

from __future__ import annotations

from tkinter import ttk

from ..audit import Severity, audit_timetable
from ..domain import Timetable


class AuditTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="App.TFrame")
        heading = ttk.Frame(self, style="Card.TFrame", padding=(18, 14))
        heading.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(heading, text="Timetable audit", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            heading,
            text=(
                "Checks daily school coverage, double-bookings, PE/RSP educator-day "
                "capacity, staff names, and resilience in larger schools."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))
        self.tree = ttk.Treeview(
            self,
            columns=("severity", "code", "teacher", "school", "day", "detail"),
            show="headings",
        )
        for column, title, width in (
            ("severity", "Level", 90),
            ("code", "Check", 145),
            ("teacher", "Teacher", 185),
            ("school", "School", 125),
            ("day", "Day", 105),
            ("detail", "Detail", 650),
        ):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width)
        self.tree.tag_configure("error", background="#FFF0F0")
        self.tree.tag_configure("warning", background="#FFF7E8")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def show(self, timetable: Timetable) -> None:
        self.tree.delete(*self.tree.get_children())
        issues = audit_timetable(timetable)
        for issue in issues:
            tag = "error" if issue.severity == Severity.ERROR else "warning"
            self.tree.insert(
                "",
                "end",
                values=(
                    issue.severity.value,
                    issue.code,
                    issue.teacher or "—",
                    issue.school or "—",
                    issue.day or "—",
                    issue.detail,
                ),
                tags=(tag,),
            )
        if not issues:
            self.tree.insert(
                "", "end", values=("Ready", "ALL_CHECKS", "—", "—", "—", "No issues found.")
            )
