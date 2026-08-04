"""Application shell and user workflows."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..domain import ChangeLogEntry, TeacherLock, TeacherRestriction, WeeklyRule
from ..exports import export_csv, export_excel
from ..models import TransferRequest, TransferType
from ..optimizer import TransferEngine
from ..repository import TimetableRepository
from .audit_tab import AuditTab
from .constraints_tabs import LocksTab, RestrictionsTab, WeeklyRulesTab, set_constraint_options
from .dashboard_tab import DashboardTab
from .rebalance_tab import ANY_SCHOOL, TransferTab
from .report_tabs import ChangeLogTab, MovementTab
from .theme import COLORS, configure_theme
from .timetable_tab import TimetableTab


class TimetableApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Peripatetic Timetable Planner")
        self.geometry("1540x920")
        self.minsize(1160, 720)
        configure_theme(self)
        self.repository = TimetableRepository()
        try:
            self.timetable = self.repository.load()
        except (OSError, ValueError) as exc:
            self.timetable = self.repository.load_baseline()
            self.after_idle(
                lambda error=exc: messagebox.showerror(
                    "Working data could not be loaded", str(error)
                )
            )
        self.preview = None
        self.requests: list[TransferRequest] = []
        self.preview_changes = ()
        self.pages: dict[str, ttk.Frame] = {}
        self._build()
        self.refresh_all()

    @property
    def active_timetable(self):
        return self.preview or self.timetable

    def _build(self) -> None:
        self._build_header()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(10, 5))

        self.dashboard_tab = DashboardTab(self.notebook, self.open_page)
        self.timetable_tab = TimetableTab(self.notebook)
        self.transfer_tab = TransferTab(
            self.notebook,
            {
                "add": self.add_request,
                "remove": self.remove_request,
                "clear_requests": self.clear_requests,
                "generate": self.generate_preview,
                "apply": self.apply_preview,
                "teacher_changed": self.update_transfer_sources,
            },
        )
        self.audit_tab = AuditTab(self.notebook)
        self.restrictions_tab = RestrictionsTab(
            self.notebook, self.add_restriction, self.delete_restriction
        )
        self.locks_tab = LocksTab(self.notebook, self.add_lock, self.delete_lock)
        self.rules_tab = WeeklyRulesTab(
            self.notebook, self.add_weekly_rule, self.delete_weekly_rule
        )
        self.movement_tab = MovementTab(self.notebook)
        self.log_tab = ChangeLogTab(self.notebook)
        page_specs = (
            ("dashboard", self.dashboard_tab, "Overview"),
            ("timetable", self.timetable_tab, "Timetable"),
            ("transfers", self.transfer_tab, "Transfer planner"),
            ("audit", self.audit_tab, "Audit"),
            ("restrictions", self.restrictions_tab, "Restrictions"),
            ("locks", self.locks_tab, "Locks"),
            ("rules", self.rules_tab, "Weekly rules"),
            ("movement", self.movement_tab, "Teacher movement"),
            ("history", self.log_tab, "History"),
        )
        for key, page, title in page_specs:
            self.pages[key] = page
            self.notebook.add(page, text=title)

        status_bar = tk.Frame(self, bg="#E1E7EC", height=30)
        status_bar.pack(fill="x", side="bottom")
        self.status = tk.Label(
            status_bar,
            text="",
            bg="#E1E7EC",
            fg=COLORS["muted"],
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status.pack(fill="x", padx=14, pady=6)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["navy"], height=78)
        header.pack(fill="x")
        title = tk.Frame(header, bg=COLORS["navy"])
        title.pack(side="left", padx=20, pady=12)
        tk.Label(
            title,
            text="Peripatetic Timetable Planner",
            bg=COLORS["navy"],
            fg="white",
            font=("Segoe UI Semibold", 20),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="St Nicholas College  •  2026/2027  •  safe, explainable transfer planning",
            bg=COLORS["navy"],
            fg="#CCDBE5",
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        buttons = tk.Frame(header, bg=COLORS["navy"])
        buttons.pack(side="right", padx=16, pady=17)
        ttk.Button(
            buttons,
            text="Restore 29 July baseline",
            style="Warning.TButton",
            command=self.restore_original,
        ).pack(side="right", padx=4)
        ttk.Button(
            buttons,
            text="Export Excel",
            style="Success.TButton",
            command=self.export_excel_file,
        ).pack(side="right", padx=4)
        ttk.Button(
            buttons,
            text="Export CSV",
            style="Primary.TButton",
            command=self.export_csv_file,
        ).pack(side="right", padx=4)
        self.discard_button = ttk.Button(
            buttons,
            text="Discard preview",
            style="Secondary.TButton",
            command=self.discard_preview,
            state="disabled",
        )
        self.discard_button.pack(side="right", padx=4)

    def open_page(self, name: str) -> None:
        page = self.pages.get(name)
        if page is not None:
            self.notebook.select(page)

    def refresh_all(self) -> None:
        active = self.active_timetable
        self.dashboard_tab.show(active)
        self.timetable_tab.show(active, self.preview is not None)
        self.transfer_tab.set_options(self.timetable.teachers, self.timetable.school_names)
        self.transfer_tab.show_requests(self.requests, self.timetable)
        set_constraint_options(
            (self.restrictions_tab, self.locks_tab, self.rules_tab),
            self.timetable.teachers,
            self.timetable.school_names,
        )
        self.restrictions_tab.show(self.timetable.restrictions)
        self.locks_tab.show(self.timetable.locks)
        self.rules_tab.show(self.timetable.weekly_rules)
        self.movement_tab.show(active)
        self.audit_tab.show(active)
        self.log_tab.show(self.timetable)
        self.discard_button.configure(state="normal" if self.preview else "disabled")
        self.status.configure(
            text=(
                "Preview active — review the highlighted placements before applying"
                if self.preview
                else "Working copy saved locally • source baseline remains protected"
            )
        )

    def update_transfer_sources(self) -> None:
        teacher = self.transfer_tab.teacher.get()
        schools = tuple(
            school
            for school in self.timetable.school_names
            if self.timetable.assignments_for(teacher=teacher, school=school)
        )
        self.transfer_tab.set_source_options(schools)

    def add_request(self) -> None:
        teacher = self.transfer_tab.teacher.get()
        source = self.transfer_tab.source.get()
        type_text = self.transfer_tab.transfer_type.get()
        try:
            transfer_type = TransferType(type_text)
        except ValueError:
            transfer_type = TransferType.PARTIAL
        days = self.transfer_tab.selected_days()
        if not teacher or not source:
            messagebox.showwarning(
                "Request incomplete", "Select a teacher and their current school."
            )
            return
        if transfer_type == TransferType.PARTIAL and not days:
            messagebox.showwarning(
                "Request incomplete", "Choose at least one day for a partial transfer."
            )
            return
        invalid_days = [
            day for day in days if source not in self.timetable.schools_for_teacher(teacher, day)
        ]
        if invalid_days:
            messagebox.showwarning(
                "Days do not match the source school",
                f"{teacher} is not at {source} on {', '.join(invalid_days)}.",
            )
            return
        destination = self.transfer_tab.destination.get()
        preferred = "" if destination in ("", ANY_SCHOOL) else destination
        request = TransferRequest(
            teacher=teacher,
            source_school=source,
            transfer_type=transfer_type,
            days=days,
            preferred_school=preferred,
            excluded_schools=self.transfer_tab.excluded_schools(),
        )
        if request not in self.requests:
            self.requests.append(request)
        self.preview, self.preview_changes = None, ()
        self.transfer_tab.reset_builder()
        self.transfer_tab.show_requests(self.requests, self.timetable)
        self.status.configure(text="Transfer request added to the planning queue.")

    def remove_request(self) -> None:
        index = self.transfer_tab.selected_request_index()
        if index is not None:
            self.requests.pop(index)
            self.preview, self.preview_changes = None, ()
            self.refresh_all()

    def clear_requests(self) -> None:
        self.requests.clear()
        self.preview, self.preview_changes = None, ()
        self.transfer_tab.show_result((), "No preview generated.", False)
        self.refresh_all()

    def generate_preview(self) -> None:
        result = TransferEngine(self.timetable).solve(self.requests)
        if not result.succeeded:
            self.preview, self.preview_changes = None, ()
            self.transfer_tab.show_result(
                (),
                f"PLAN BLOCKED\n\n{result.error}\n\nOptions checked: {result.explored_states}",
                False,
            )
            self.refresh_all()
            self.open_page("transfers")
            return
        self.preview, self.preview_changes = result.timetable, result.changes
        details = "\n".join(
            f"{change.note}\n   Reason: {change.rationale}" for change in result.changes
        )
        self.transfer_tab.show_result(
            result.changes,
            f"SAFE PREVIEW READY\n\n{details}\n\nOptions checked: {result.explored_states}.",
            True,
        )
        self.refresh_all()
        self.open_page("timetable")

    def apply_preview(self) -> None:
        if self.preview is None:
            return
        next_number = sum(
            entry.version.startswith("T") for entry in self.timetable.change_log
        ) + 1
        note = "Transfer plan: " + " | ".join(
            change.note for change in self.preview_changes
        )
        self.preview.change_log.append(ChangeLogEntry(f"T{next_number}", note))
        try:
            self.repository.save(self.preview)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save", str(exc))
            return
        self.timetable = self.preview
        self.preview, self.preview_changes, self.requests = None, (), []
        self.transfer_tab.show_result((), "Transfer plan applied and saved.", False)
        self.refresh_all()
        messagebox.showinfo(
            "Transfer plan applied", "The approved preview is now the saved working timetable."
        )

    def discard_preview(self) -> None:
        self.preview, self.preview_changes = None, ()
        if hasattr(self, "transfer_tab"):
            self.transfer_tab.show_result((), "No preview generated.", False)
        if hasattr(self, "dashboard_tab"):
            self.refresh_all()

    def add_restriction(self) -> None:
        teacher, school, days, reason = self.restrictions_tab.values()
        if not teacher or not school or not days:
            messagebox.showwarning(
                "Restriction incomplete", "Select a teacher, school, and at least one day."
            )
            return
        item = TeacherRestriction(teacher, school, days, reason)
        if item not in self.timetable.restrictions:
            self.timetable.restrictions.append(item)
            self._save_constraints("Restriction added.")

    def delete_restriction(self) -> None:
        self._delete_constraint(
            self.restrictions_tab, self.timetable.restrictions, "Restriction removed."
        )

    def add_lock(self) -> None:
        teacher, day, school = self.locks_tab.values()
        if not teacher or not day or not school:
            messagebox.showwarning(
                "Lock incomplete", "Select a teacher, day, and school."
            )
            return
        if school not in self.timetable.schools_for_teacher(teacher, day):
            messagebox.showwarning(
                "Invalid lock", f"{teacher} is not assigned to {school} on {day}."
            )
            return
        item = TeacherLock(teacher, day, school)
        if item not in self.timetable.locks:
            self.timetable.locks.append(item)
            self._save_constraints("Placement locked.")

    def delete_lock(self) -> None:
        self._delete_constraint(self.locks_tab, self.timetable.locks, "Lock removed.")

    def add_weekly_rule(self) -> None:
        teacher, school, kind, times = self.rules_tab.values()
        try:
            count = int(times)
        except ValueError:
            count = -1
        if not teacher or not school or kind not in ("EXACT", "MIN", "MAX") or not 0 <= count <= 5:
            messagebox.showwarning(
                "Rule incomplete", "Select the teacher, school, rule type, and a number from 0 to 5."
            )
            return
        self.timetable.weekly_rules = [
            rule
            for rule in self.timetable.weekly_rules
            if not (rule.teacher == teacher and rule.school == school and rule.kind == kind)
        ]
        self.timetable.weekly_rules.append(WeeklyRule(teacher, school, kind, count))
        self._save_constraints("Weekly rule saved.")

    def delete_weekly_rule(self) -> None:
        self._delete_constraint(self.rules_tab, self.timetable.weekly_rules, "Rule removed.")

    def _delete_constraint(self, tab, collection, message: str) -> None:
        index = tab.selected_index()
        if index is not None:
            collection.pop(index)
            self._save_constraints(message)

    def _save_constraints(self, message: str) -> None:
        self.preview, self.preview_changes = None, ()
        try:
            self.repository.save(self.timetable)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save", str(exc))
            return
        self.refresh_all()
        self.status.configure(text=message)

    def restore_original(self) -> None:
        if not messagebox.askyesno(
            "Restore the 29 July baseline",
            "This replaces the working copy, locks, restrictions, rules, and history. Continue?",
        ):
            return
        try:
            self.timetable = self.repository.restore_baseline()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not restore", str(exc))
            return
        self.preview, self.preview_changes, self.requests = None, (), []
        self.refresh_all()
        self.status.configure(text="The verified 29 July baseline has been restored.")

    def export_csv_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export timetable as CSV",
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv")],
            initialfile="peripatetic_timetable.csv",
        )
        if path:
            try:
                export_csv(self.active_timetable, path)
            except OSError as exc:
                messagebox.showerror("Could not export CSV", str(exc))
                return
            self.status.configure(text=f"CSV exported to {path}")

    def export_excel_file(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Export timetable as Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile="peripatetic_timetable.xlsx",
        )
        if not path:
            return
        try:
            export_excel(self.active_timetable, path)
        except ImportError:
            messagebox.showerror(
                "Excel support missing", "Install the packages listed in requirements.txt."
            )
            return
        except OSError as exc:
            messagebox.showerror("Could not export Excel", str(exc))
            return
        self.status.configure(text=f"Excel workbook exported to {path}")
