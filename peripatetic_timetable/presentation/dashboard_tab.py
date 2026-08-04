"""At-a-glance project dashboard."""

from __future__ import annotations

from tkinter import ttk

from ..audit import Severity, audit_timetable
from ..domain import Timetable
from .theme import COLORS


class DashboardTab(ttk.Frame):
    def __init__(self, parent, open_page):
        super().__init__(parent, style="App.TFrame")
        self.open_page = open_page
        self.metrics: dict[str, ttk.Label] = {}
        self._build()

    def _build(self) -> None:
        hero = ttk.Frame(self, style="Hero.TFrame", padding=(22, 18))
        hero.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(hero, text="2026/2027 planning workspace", style="HeroTitle.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            hero,
            text=(
                "Start from the approved 29 July timetable, protect fixed placements, "
                "and test full or partial transfers before committing anything."
            ),
            style="HeroText.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        metrics = ttk.Frame(self, style="App.TFrame")
        metrics.pack(fill="x", padx=10, pady=6)
        for key, title, accent in (
            ("schools", "Schools", COLORS["blue"]),
            ("teachers", "Active teachers", COLORS["green"]),
            ("placements", "Daily placements", COLORS["navy"]),
            ("issues", "Audit issues", COLORS["orange"]),
        ):
            card = ttk.Frame(metrics, style="Card.TFrame", padding=(16, 12))
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            marker = ttk.Label(card, text="●", foreground=accent, background="white")
            marker.pack(side="left", padx=(0, 9))
            value = ttk.Label(card, text="0", style="Metric.TLabel")
            value.pack(side="left")
            ttk.Label(card, text=title, style="Muted.TLabel").pack(side="left", padx=(8, 0))
            self.metrics[key] = value

        content = ttk.Panedwindow(self, orient="horizontal")
        content.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        issues = ttk.Frame(content, style="Card.TFrame", padding=14)
        notes = ttk.Frame(content, style="Card.TFrame", padding=14)
        content.add(issues, weight=3)
        content.add(notes, weight=2)
        ttk.Label(issues, text="Items needing attention", style="Section.TLabel").pack(
            anchor="w"
        )
        self.issue_tree = ttk.Treeview(
            issues,
            columns=("severity", "item", "detail"),
            show="headings",
            height=9,
        )
        for column, title, width in (
            ("severity", "Level", 90),
            ("item", "Check", 230),
            ("detail", "What it means", 520),
        ):
            self.issue_tree.heading(column, text=title)
            self.issue_tree.column(column, width=width)
        self.issue_tree.tag_configure("error", background="#FFF0F0")
        self.issue_tree.tag_configure("warning", background="#FFF7E8")
        self.issue_tree.pack(fill="both", expand=True, pady=(8, 10))
        ttk.Button(
            issues,
            text="Open full audit",
            style="Primary.TButton",
            command=lambda: self.open_page("audit"),
        ).pack(anchor="e")

        ttk.Label(notes, text="Staffing notes from the source", style="Section.TLabel").pack(
            anchor="w"
        )
        self.note_tree = ttk.Treeview(
            notes, columns=("name", "status", "note"), show="headings", height=9
        )
        for column, title, width in (
            ("name", "Person / post", 175),
            ("status", "Status", 120),
            ("note", "Note", 280),
        ):
            self.note_tree.heading(column, text=title)
            self.note_tree.column(column, width=width)
        self.note_tree.pack(fill="both", expand=True, pady=(8, 10))
        ttk.Button(
            notes,
            text="Plan a transfer",
            style="Success.TButton",
            command=lambda: self.open_page("transfers"),
        ).pack(anchor="e")

    def show(self, timetable: Timetable) -> None:
        issues = audit_timetable(timetable)
        values = {
            "schools": len(timetable.schools),
            "teachers": len(timetable.teachers),
            "placements": len(timetable.assignments),
            "issues": len(issues),
        }
        for key, value in values.items():
            self.metrics[key].configure(text=str(value))
        self.issue_tree.delete(*self.issue_tree.get_children())
        for issue in issues:
            tag = "error" if issue.severity == Severity.ERROR else "warning"
            self.issue_tree.insert(
                "", "end", values=(issue.severity.value, issue.title, issue.detail), tags=(tag,)
            )
        if not issues:
            self.issue_tree.insert("", "end", values=("Ready", "No issues", "All active checks pass."))
        self.note_tree.delete(*self.note_tree.get_children())
        for note in timetable.staff_notes:
            self.note_tree.insert("", "end", values=(note.name, note.status, note.note))
