"""Application shell and user workflows."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from ..audit import teacher_has_full_name
from ..config import DAYS
from ..domain import (
    ChangeLogEntry,
    StaffNote,
    TeacherLock,
    TeacherRestriction,
    WeeklyRule,
    normalise,
)
from ..emergency import EmergencyEngine, EmergencyReason
from ..exports import available_export_copy, export_csv, export_excel
from ..models import TransferRequest, TransferType
from ..optimizer import TransferEngine
from ..repository import BASELINE_SNAPSHOT_ID, TimetableRepository
from .audit_tab import AuditTab
from .constraints_tabs import LocksTab, RestrictionsTab, WeeklyRulesTab, set_constraint_options
from .dashboard_tab import DashboardTab
from .emergency_tab import EmergencyTab
from .new_teacher_dialog import ask_new_teacher
from .rebalance_tab import ANY_SCHOOL, TransferTab
from .report_tabs import ChangeLogTab, MovementTab
from .staff_tab import StaffTab
from .theme import COLORS, configure_theme
from .timetable_tab import TimetableTab


class TimetableApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Peripatetic Timetable Planner")
        self.geometry("1440x860")
        self.minsize(1100, 700)
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
        self._ensure_initial_snapshot()
        self.preview = None
        self.preview_kind = ""
        self.requests: list[TransferRequest] = []
        self.preview_changes = ()
        self.emergency_teacher = ""
        self.emergency_reason = EmergencyReason.SICK_LEAVE
        self._prompted_incomplete_names: set[str] = set()
        self.pages: dict[str, ttk.Frame] = {}
        self._build()
        self.refresh_all()
        self.after_idle(self._maximise_window)
        self.after(600, self.prompt_for_incomplete_names)

    def _maximise_window(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

    @property
    def active_timetable(self):
        return self.preview or self.timetable

    def _build(self) -> None:
        self._build_header()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(5, 3))

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
        self.emergency_tab = EmergencyTab(
            self.notebook,
            {
                "generate": self.generate_emergency_preview,
                "apply": self.apply_emergency_preview,
                "plan_another": self.plan_another_emergency_teacher,
                "selection_changed": self.emergency_selection_changed,
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
        self.staff_tab = StaffTab(
            self.notebook,
            {
                "save_note": self.save_staff_note,
                "delete_note": self.delete_staff_note,
                "add_teacher": self.add_teacher,
                "rename_teacher": self.rename_teacher,
                "remove_teacher": self.remove_teacher,
            },
        )
        self.movement_tab = MovementTab(self.notebook)
        self.log_tab = ChangeLogTab(self.notebook, self.restore_history_version)
        page_specs = (
            ("dashboard", self.dashboard_tab, "Overview"),
            ("timetable", self.timetable_tab, "Timetable"),
            ("transfers", self.transfer_tab, "Transfer planner"),
            ("emergency", self.emergency_tab, "Emergency"),
            ("audit", self.audit_tab, "Audit"),
            ("restrictions", self.restrictions_tab, "Restrictions"),
            ("locks", self.locks_tab, "Locks"),
            ("rules", self.rules_tab, "Weekly rules"),
            ("staff", self.staff_tab, "Staff"),
            ("movement", self.movement_tab, "Movement"),
            ("history", self.log_tab, "History"),
        )
        for key, page, title in page_specs:
            self.pages[key] = page
            self.notebook.add(page, text=title)

        status_bar = tk.Frame(self, bg="#E1E7EC", height=24)
        status_bar.pack(fill="x", side="bottom")
        self.status = tk.Label(
            status_bar,
            text="",
            bg="#E1E7EC",
            fg=COLORS["muted"],
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.status.pack(fill="x", padx=10, pady=3)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=COLORS["navy"], height=64)
        header.pack(fill="x")
        title = tk.Frame(header, bg=COLORS["navy"])
        title.pack(side="left", padx=16, pady=8)
        tk.Label(
            title,
            text="Peripatetic Timetable Planner",
            bg=COLORS["navy"],
            fg="white",
            font=("Segoe UI Semibold", 18),
        ).pack(anchor="w")
        tk.Label(
            title,
            text=(
                "St Nicholas College  •  2026/2027  •  safe transfer and emergency planning"
            ),
            bg=COLORS["navy"],
            fg="#CCDBE5",
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        buttons = tk.Frame(header, bg=COLORS["navy"])
        buttons.pack(side="right", padx=12, pady=12)
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
        self.transfer_tab.set_options(
            {
                teacher: self.timetable.subjects_for_teacher(teacher)
                for teacher in self.timetable.teachers
            },
            self.timetable.school_names,
        )
        self.emergency_tab.set_options(
            {
                teacher: self.timetable.subjects_for_teacher(teacher)
                for teacher in self.timetable.teachers
            }
        )
        self.update_transfer_sources()
        self.transfer_tab.show_requests(self.requests, self.timetable)
        set_constraint_options(
            (self.restrictions_tab, self.locks_tab, self.rules_tab),
            self.timetable.teachers,
            self.timetable.school_names,
        )
        self.restrictions_tab.show(self.timetable.restrictions)
        self.locks_tab.show(self.timetable.locks)
        self.rules_tab.show(self.timetable.weekly_rules)
        self.staff_tab.show(self.timetable)
        self.movement_tab.show(active)
        self.audit_tab.show(active)
        self.log_tab.show(self.timetable, self.repository.list_snapshots())
        self.discard_button.configure(state="normal" if self.preview else "disabled")
        self.status.configure(
            text=(
                "Emergency preview active — review the highlighted timetable before applying"
                if self.preview_kind == "emergency"
                else "Transfer preview active — review the highlighted placements before applying"
                if self.preview
                else "Working copy saved locally • source baseline remains protected"
            )
        )

    def update_transfer_sources(self) -> None:
        teacher = self.transfer_tab.selected_teacher()
        schools = tuple(
            school
            for school in self.timetable.school_names
            if self.timetable.assignments_for(teacher=teacher, school=school)
        )
        self.transfer_tab.set_source_options(schools)

    def add_request(self) -> None:
        teacher = self.transfer_tab.selected_teacher()
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
        self.preview, self.preview_kind, self.preview_changes = None, "", ()
        self.transfer_tab.reset_builder()
        self.transfer_tab.show_requests(self.requests, self.timetable)
        self.status.configure(text="Transfer request added to the planning queue.")

    def remove_request(self) -> None:
        index = self.transfer_tab.selected_request_index()
        if index is not None:
            self.requests.pop(index)
            self.preview, self.preview_kind, self.preview_changes = None, "", ()
            self.refresh_all()

    def clear_requests(self) -> None:
        self.requests.clear()
        self.preview, self.preview_kind, self.preview_changes = None, "", ()
        self.transfer_tab.show_result((), "No preview generated.", False)
        self.refresh_all()

    def generate_preview(self) -> None:
        result = TransferEngine(self.timetable).solve(self.requests)
        if not result.succeeded:
            self.preview, self.preview_kind, self.preview_changes = None, "", ()
            self.transfer_tab.show_result(
                (),
                f"PLAN BLOCKED\n\n{result.error}\n\nOptions checked: {result.explored_states}",
                False,
            )
            self.refresh_all()
            self.open_page("transfers")
            return
        self.preview = result.timetable
        self.preview_kind = "transfer"
        self.preview_changes = result.changes
        swap_count = len(result.changes)
        request_count = len(self.requests)
        self.transfer_tab.show_result(
            result.changes,
            "SAFE PREVIEW READY\n\n"
            f"{swap_count} swap{'s' if swap_count != 1 else ''} satisfy "
            f"{request_count} request{'s' if request_count != 1 else ''} and all active rules. "
            "Review the table above, then apply or discard the preview.\n"
            f"Options checked: {result.explored_states}.",
            True,
        )
        self.refresh_all()
        self.open_page("transfers")
        self.status.configure(
            text="Safe preview ready • review the proposed swaps, then apply or open Timetable"
        )

    def generate_emergency_preview(self) -> None:
        teacher = self.emergency_tab.selected_teacher()
        if not teacher:
            messagebox.showwarning(
                "No educator selected", "Select the educator who is unavailable."
            )
            return
        if not self.emergency_tab.confirmed.get():
            messagebox.showwarning(
                "Educator not marked unavailable",
                "Tick the unavailable educator before generating the emergency timetable.",
            )
            return

        reason = self.emergency_tab.selected_reason()
        result = EmergencyEngine(self.timetable).solve(teacher)
        if not result.succeeded:
            self.preview, self.preview_kind, self.preview_changes = None, "", ()
            self.emergency_teacher = ""
            self.emergency_tab.show_result(
                (),
                f"EMERGENCY PLAN BLOCKED\n\n{result.error}\n\n"
                f"Complete plans checked: {result.explored_plans}.",
                False,
            )
            self.refresh_all()
            self.open_page("emergency")
            return

        self.preview = result.timetable
        self.preview_kind = "emergency"
        self.preview_changes = result.changes
        self.emergency_teacher = result.unavailable_teacher
        self.emergency_reason = reason
        self.transfer_tab.show_result((), "No preview generated.", False)
        moved = sum(bool(change.cover_teacher) for change in result.changes)
        warning_text = (
            "\n\nCover warnings:\n• " + "\n• ".join(result.warnings)
            if result.warnings
            else "\n\nAll affected days retain at least one compatible educator at every school."
        )
        self.emergency_tab.show_result(
            result.changes,
            "EMERGENCY PREVIEW READY\n\n"
            f"{result.unavailable_teacher} is removed from the preview. "
            f"{moved} same-subject reassignment{'s' if moved != 1 else ''} spread the "
            "reduced cover across the week. Review the table and the highlighted timetable "
            "before applying."
            f"{warning_text}\n\nComplete plans checked: {result.explored_plans}.",
            True,
        )
        self.refresh_all()
        self.open_page("emergency")
        self.status.configure(
            text="Emergency preview ready • review it on Emergency and Timetable before applying"
        )

    def emergency_selection_changed(self) -> None:
        if self.preview_kind != "emergency":
            return
        self.preview, self.preview_kind, self.preview_changes = None, "", ()
        self.emergency_teacher = ""
        self.emergency_tab.show_result(
            (), "Selection changed — generate a new emergency preview.", False
        )
        self.refresh_all()
        self.open_page("emergency")

    def plan_another_emergency_teacher(self) -> None:
        """Discard the current emergency draft and clear its educator selection."""
        if self.preview_kind == "emergency":
            self.preview, self.preview_kind, self.preview_changes = None, "", ()
        self.emergency_teacher = ""
        self.emergency_reason = EmergencyReason.SICK_LEAVE
        self.refresh_all()
        self.emergency_tab.prepare_another_teacher()
        self.open_page("emergency")
        self.status.configure(
            text="Emergency planner cleared • select and tick another unavailable educator"
        )

    def apply_emergency_preview(self) -> None:
        if self.preview is None or self.preview_kind != "emergency":
            return
        if not messagebox.askyesno(
            "Apply emergency timetable",
            f"Save this emergency timetable for {self.emergency_teacher} "
            f"({self.emergency_reason.value})?\n\n"
            "The current saved timetable will be kept as a dated restore point.",
        ):
            return

        version = f"E{self._next_history_number('E')}"
        plan_note = " | ".join(change.note for change in self.preview_changes)
        note = (
            f"Emergency timetable for {self.emergency_teacher} "
            f"({self.emergency_reason.value}): {plan_note}"
        )
        self.preview.change_log.append(ChangeLogEntry(version, note))
        absence_note = f"Emergency timetable applied on {datetime.now():%d %b %Y}."
        status = (
            "Sick leave"
            if self.emergency_reason == EmergencyReason.SICK_LEAVE
            else "Left college"
        )
        matching_index = next(
            (
                index
                for index, item in enumerate(self.preview.staff_notes)
                if normalise(item.name) == normalise(self.emergency_teacher)
            ),
            None,
        )
        if matching_index is None:
            self.preview.staff_notes.append(
                StaffNote(self.emergency_teacher, status, absence_note)
            )
        else:
            existing = self.preview.staff_notes[matching_index]
            combined = " ".join(value for value in (existing.note, absence_note) if value)
            self.preview.staff_notes[matching_index] = StaffNote(
                existing.name, status, combined
            )

        try:
            self.repository.save_snapshot(
                self.timetable,
                f"Before {version} emergency timetable for {self.emergency_teacher}",
            )
            self.repository.save(self.preview)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save emergency timetable", str(exc))
            return
        self.timetable = self.preview
        applied_teacher = self.emergency_teacher
        applied_reason = self.emergency_reason
        self.preview, self.preview_kind, self.preview_changes = None, "", ()
        self.emergency_teacher = ""
        self.requests.clear()
        try:
            self.repository.save_snapshot(
                self.timetable,
                f"{version} approved emergency timetable",
            )
        except (OSError, ValueError) as exc:
            messagebox.showwarning(
                "Emergency timetable saved without a final restore point",
                f"The pre-emergency restore point is safe, but the final restore point failed:\n{exc}",
            )
        self.refresh_all()
        self.emergency_tab.show_result(
            (),
            f"{version} emergency timetable applied for {applied_teacher} "
            f"({applied_reason.value}).",
            False,
        )
        self.open_page("emergency")
        self.status.configure(text=f"{version} emergency timetable saved locally")
        messagebox.showinfo(
            "Emergency timetable applied",
            "The emergency timetable is now active. The previous timetable is available "
            "from History when the educator returns or if the plan must be reversed.",
        )

    def apply_preview(self) -> None:
        if self.preview is None or self.preview_kind != "transfer":
            return
        next_number = self._next_history_number("T")
        version = f"T{next_number}"
        note = "Transfer plan: " + " | ".join(
            change.note for change in self.preview_changes
        )
        self.preview.change_log.append(ChangeLogEntry(version, note))
        try:
            self.repository.save(self.preview)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save", str(exc))
            return
        self.timetable = self.preview
        self.preview, self.preview_kind, self.preview_changes, self.requests = None, "", (), []
        try:
            self.repository.save_snapshot(
                self.timetable,
                f"{version} approved transfer plan",
            )
        except (OSError, ValueError) as exc:
            messagebox.showwarning(
                "Timetable saved without a restore point",
                f"The approved timetable was saved, but its dated restore point failed:\n{exc}",
            )
        self.transfer_tab.show_result((), "Transfer plan applied and saved.", False)
        self.refresh_all()
        messagebox.showinfo(
            "Transfer plan applied", "The approved preview is now the saved working timetable."
        )

    def discard_preview(self) -> None:
        self.preview, self.preview_kind, self.preview_changes = None, "", ()
        self.emergency_teacher = ""
        if hasattr(self, "transfer_tab"):
            self.transfer_tab.show_result((), "No preview generated.", False)
        if hasattr(self, "emergency_tab"):
            self.emergency_tab.reset()
        if hasattr(self, "dashboard_tab"):
            self.refresh_all()

    def save_staff_note(self) -> None:
        name, status, note = self.staff_tab.note_values()
        if not name or not status:
            messagebox.showwarning(
                "Staffing note incomplete",
                "Enter the person or post and its current status.",
            )
            return
        updated = self.timetable.clone()
        item = StaffNote(name, status, note)
        index = self.staff_tab.selected_note_index()
        if index is None:
            updated.staff_notes.append(item)
            action = f"Added staffing note for {name}."
        else:
            updated.staff_notes[index] = item
            action = f"Updated staffing note for {name}."
        if self._commit_staff_update(updated, action):
            self.staff_tab.clear_note_form()

    def prompt_for_incomplete_names(self) -> None:
        for teacher in self.timetable.teachers:
            if teacher_has_full_name(teacher) or teacher in self._prompted_incomplete_names:
                continue
            self._prompted_incomplete_names.add(teacher)
            full_name = simpledialog.askstring(
                "Full teacher name required",
                f"{teacher} does not include both a first name and surname.\n\n"
                "Enter the teacher's full name, or select Cancel to correct it later in Staff:",
                initialvalue=f"{teacher} ",
                parent=self,
            )
            if full_name is None:
                continue
            full_name = full_name.strip()
            if not teacher_has_full_name(full_name):
                messagebox.showwarning(
                    "Full name still required",
                    "Enter at least a first name and surname. The Audit warning will remain.",
                )
                continue
            if any(
                normalise(existing) == normalise(full_name)
                for existing in self.timetable.teachers
                if normalise(existing) != normalise(teacher)
            ):
                messagebox.showwarning(
                    "Teacher already exists",
                    "That full name already belongs to an active teacher.",
                )
                continue
            updated = self.timetable.clone()
            updated.rename_teacher(teacher, full_name)
            self._commit_staff_update(updated, f"Renamed {teacher} to {full_name}.")

    def delete_staff_note(self) -> None:
        index = self.staff_tab.selected_note_index()
        if index is None:
            messagebox.showwarning("No note selected", "Select the staffing note to delete.")
            return
        item = self.timetable.staff_notes[index]
        if not messagebox.askyesno(
            "Delete staffing note",
            f"Delete the staffing note for {item.name}?",
        ):
            return
        updated = self.timetable.clone()
        updated.staff_notes.pop(index)
        if self._commit_staff_update(updated, f"Deleted staffing note for {item.name}."):
            self.staff_tab.clear_note_form()

    def add_teacher(self) -> None:
        subjects = tuple(
            sorted({item.subject for item in self.timetable.assignments}, key=str.casefold)
        )
        details = ask_new_teacher(
            self,
            tuple(self.timetable.school_names),
            subjects,
            tuple(self.timetable.teachers),
        )
        if details is None:
            return
        updated = self.timetable.clone()
        try:
            added = updated.add_teacher(details.name, details.subject, details.placements)
        except ValueError as exc:
            messagebox.showwarning("Could not add teacher", str(exc))
            return
        subject = updated.subjects_for_teacher(details.name)[0]
        placement_summary = ", ".join(
            f"{day[:3]} {details.placements[day]}" for day in DAYS
        )
        note = (
            f"Added {details.name} ({subject}) as additional staff with {added} placements: "
            f"{placement_summary}."
        )
        if self._commit_staff_update(updated, note):
            messagebox.showinfo(
                "Teacher added",
                f"{details.name} has been added as additional {subject} staff.\n\n"
                "The teacher now appears in the timetable, transfer planner, Emergency page, "
                "rules, locks, and movement report.",
            )

    def rename_teacher(self) -> None:
        current_name = self.staff_tab.teacher.get()
        new_name = self.staff_tab.new_name.get().strip()
        if not current_name or not new_name:
            messagebox.showwarning(
                "Teacher name incomplete",
                "Select the current teacher and enter the new name.",
            )
            return
        if normalise(current_name) == normalise(new_name):
            messagebox.showwarning("Name unchanged", "Enter a different teacher name.")
            return
        if any(normalise(teacher) == normalise(new_name) for teacher in self.timetable.teachers):
            messagebox.showwarning(
                "Teacher already exists",
                "That name already belongs to an active teacher. Names cannot be merged here.",
            )
            return
        if not messagebox.askyesno(
            "Rename teacher",
            f"Rename {current_name} to {new_name} everywhere in the timetable?",
        ):
            return
        updated = self.timetable.clone()
        updated.rename_teacher(current_name, new_name)
        if self._commit_staff_update(updated, f"Renamed {current_name} to {new_name}."):
            self.staff_tab.clear_teacher_form()

    def remove_teacher(self) -> None:
        teacher = self.staff_tab.teacher.get()
        if not teacher:
            messagebox.showwarning("No teacher selected", "Select the teacher to remove.")
            return
        placements = self.timetable.assignments_for(teacher=teacher)
        subjects = " / ".join(self.timetable.subjects_for_teacher(teacher))
        if not messagebox.askyesno(
            "Remove teacher from the college",
            f"Remove {teacher} ({subjects}) and all {len(placements)} placements?\n\n"
            "A staffing note will remain and this change can be recovered from History.",
        ):
            return
        updated = self.timetable.clone()
        updated.remove_teacher(teacher)
        removal_note = f"Removed from the active timetable on {datetime.now():%d %b %Y}."
        matching_index = next(
            (
                index
                for index, item in enumerate(updated.staff_notes)
                if normalise(item.name) == normalise(teacher)
            ),
            None,
        )
        if matching_index is None:
            updated.staff_notes.append(StaffNote(teacher, "Left college", removal_note))
        else:
            existing = updated.staff_notes[matching_index]
            combined_note = " ".join(value for value in (existing.note, removal_note) if value)
            updated.staff_notes[matching_index] = StaffNote(
                existing.name,
                existing.status,
                combined_note,
            )
        self._commit_staff_update(
            updated,
            f"Removed {teacher} ({subjects}) and {len(placements)} placements.",
        )

    def _commit_staff_update(self, updated, note: str) -> bool:
        version = f"S{self._next_history_number('S')}"
        updated.change_log.append(ChangeLogEntry(version, note))
        try:
            self.repository.save(updated)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save staff update", str(exc))
            return False
        self.timetable = updated
        self.preview, self.preview_kind, self.preview_changes, self.requests = None, "", (), []
        try:
            self.repository.save_snapshot(updated, f"{version} staff update")
        except (OSError, ValueError) as exc:
            messagebox.showwarning(
                "Staff update saved without a restore point",
                f"The staff update was saved, but its dated restore point failed:\n{exc}",
            )
        self.refresh_all()
        self.open_page("staff")
        self.status.configure(text=note)
        return True

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
        teacher, days = self.locks_tab.values()
        if not teacher or not days:
            messagebox.showwarning(
                "Lock incomplete", "Select a teacher and at least one day."
            )
            return
        new_locks = []
        invalid_days = []
        for day in days:
            schools = self.timetable.schools_for_teacher(teacher, day)
            if len(schools) != 1:
                invalid_days.append(day)
                continue
            lock = TeacherLock(teacher, day, schools[0])
            if lock not in self.timetable.locks:
                new_locks.append(lock)
        if invalid_days:
            messagebox.showwarning(
                "Some days cannot be locked",
                f"{teacher} does not have one clear school on {', '.join(invalid_days)}.",
            )
        if new_locks:
            self.timetable.locks.extend(new_locks)
            self.locks_tab.clear_days()
            self._save_constraints(f"Added {len(new_locks)} placement lock(s).")

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
        self.preview, self.preview_kind, self.preview_changes = None, "", ()
        try:
            self.repository.save(self.timetable)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save", str(exc))
            return
        self.refresh_all()
        self.status.configure(text=message)

    def _ensure_initial_snapshot(self) -> None:
        if not self.repository.working_file.exists() or self.repository.list_snapshots():
            return
        transfer_entries = [
            entry.version for entry in self.timetable.change_log if entry.version.startswith("T")
        ]
        label = (
            f"{transfer_entries[-1]} current approved timetable"
            if transfer_entries
            else "Current saved timetable"
        )
        try:
            self.repository.save_snapshot(self.timetable, label)
        except (OSError, ValueError):
            pass

    def _next_history_number(self, prefix: str) -> int:
        versions = [entry.version for entry in self.timetable.change_log]
        versions.extend(snapshot.label.split(maxsplit=1)[0] for snapshot in self.repository.list_snapshots())
        numbers = [
            int(version[len(prefix):])
            for version in versions
            if version.startswith(prefix) and version[len(prefix):].isdigit()
        ]
        return max(numbers, default=0) + 1

    def restore_history_version(self, snapshot_id: str, display_label: str) -> None:
        if not messagebox.askyesno(
            "Restore timetable version",
            f"Restore {display_label}?\n\nYour current timetable will be preserved first.",
        ):
            return
        try:
            self.repository.save_snapshot(
                self.timetable,
                f"Preserved before restoring {display_label}",
            )
            restored = self.repository.load_snapshot(snapshot_id)
            version = f"R{self._next_history_number('R')}"
            restored.change_log.append(
                ChangeLogEntry(version, f"Restored approved version: {display_label}")
            )
            self.repository.save(restored)
            self.repository.save_snapshot(
                restored,
                f"{version} restored timetable",
            )
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not restore", str(exc))
            return
        self.timetable = restored
        self.preview, self.preview_kind, self.preview_changes, self.requests = None, "", (), []
        self.refresh_all()
        self.open_page("history")
        self.status.configure(text=f"Restored {display_label}; the previous timetable was preserved.")

    def restore_original(self) -> None:
        self.restore_history_version(
            BASELINE_SNAPSHOT_ID,
            "29 Jul 2026 — Original verified baseline",
        )

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
                "Excel support missing",
                "Close the planner and double-click START PLANNER.bat. It will install "
                "the required Excel support automatically.",
            )
            return
        except PermissionError:
            alternate_path = available_export_copy(path)
            try:
                export_excel(self.active_timetable, alternate_path)
            except OSError as exc:
                messagebox.showerror("Could not export Excel", str(exc))
                return
            messagebox.showinfo(
                "Excel export complete",
                "The selected workbook is open in Excel, so it could not be replaced. "
                "A new copy was saved instead:\n\n"
                f"{alternate_path}",
            )
            self.status.configure(text=f"Excel workbook exported to {alternate_path}")
            return
        except OSError as exc:
            messagebox.showerror("Could not export Excel", str(exc))
            return
        messagebox.showinfo(
            "Excel export complete",
            f"The timetable was exported successfully to:\n\n{path}",
        )
        self.status.configure(text=f"Excel workbook exported to {path}")
