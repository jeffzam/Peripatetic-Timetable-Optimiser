from datetime import datetime
from tkinter import ttk

from ..config import DAYS
from ..domain import Timetable
from ..reports import coverage_report, movement_matrix
from ..repository import BASELINE_SNAPSHOT_ID, HistorySnapshot

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
    def __init__(self, parent, restore_callback):
        super().__init__(parent, style="App.TFrame")
        self.restore_callback = restore_callback
        self._snapshot_by_label: dict[str, str] = {}

        restore = ttk.Frame(self, style="Card.TFrame", padding=14)
        restore.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(restore, text="Restore an approved timetable", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            restore,
            text=(
                "Choose the original baseline or any dated approval. Your current timetable "
                "is preserved before the selected version is restored."
            ),
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 9))
        self.version = ttk.Combobox(restore, state="readonly", width=62)
        self.version.grid(row=2, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(
            restore,
            text="Restore selected version",
            style="Warning.TButton",
            command=self._restore_selected,
        ).grid(row=2, column=1, sticky="e")
        restore.columnconfigure(0, weight=1)

        heading = ttk.Frame(self, style="App.TFrame")
        heading.pack(fill="x", padx=10, pady=(8, 0))
        ttk.Label(heading, text="Detailed change log", style="Section.TLabel").pack(side="left")
        self.tree = ttk.Treeview(self, columns=("version", "note"), show="headings")
        self.tree.heading("version", text="Version"); self.tree.column("version", width=110, anchor="center")
        self.tree.heading("note", text="Change"); self.tree.column("note", width=900)
        self.tree.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    @staticmethod
    def _dated_label(snapshot: HistorySnapshot) -> str:
        try:
            date = datetime.fromisoformat(snapshot.created_at).strftime("%d %b %Y, %H:%M")
        except ValueError:
            date = snapshot.created_at
        return f"{date} — {snapshot.label}"

    def _restore_selected(self) -> None:
        label = self.version.get()
        snapshot_id = self._snapshot_by_label.get(label)
        if snapshot_id:
            self.restore_callback(snapshot_id, label)

    def show(self, timetable: Timetable, snapshots: list[HistorySnapshot]):
        baseline_label = "29 Jul 2026 — Original verified baseline"
        labels = [self._dated_label(snapshot) for snapshot in snapshots]
        self._snapshot_by_label = {
            baseline_label: BASELINE_SNAPSHOT_ID,
            **{label: snapshot.snapshot_id for label, snapshot in zip(labels, snapshots)},
        }
        self.version["values"] = (baseline_label, *labels)
        if self.version.get() not in self.version["values"]:
            self.version.set(labels[0] if labels else baseline_label)
        self.tree.delete(*self.tree.get_children())
        for item in reversed(timetable.change_log):
            self.tree.insert("", "end", values=(item.version, item.note))
