"""Emergency timetable screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..emergency import EmergencyChange, EmergencyReason
from .rebalance_tab import ALL_SUBJECTS, teacher_label
from .theme import COLORS


class EmergencyTab(ttk.Frame):
    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, style="App.TFrame")
        self.callbacks = callbacks
        self.confirmed = tk.BooleanVar(value=False)
        self._teacher_subjects: dict[str, tuple[str, ...]] = {}
        self._teacher_by_label: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        intro = ttk.Frame(self, style="Card.TFrame", padding=(12, 8))
        intro.pack(fill="x", padx=6, pady=(6, 3))
        ttk.Label(intro, text="Create an emergency timetable", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            intro,
            text=(
                "Tick one unavailable educator. The planner redistributes compatible "
                "colleagues across the schools, shares reduced cover fairly, and keeps "
                "the saved timetable unchanged until you approve the preview."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        form = ttk.Frame(self, style="Card.TFrame", padding=12)
        form.pack(fill="x", padx=6, pady=3)
        for column, label in enumerate(("Subject", "Unavailable educator", "Reason")):
            ttk.Label(form, text=label, style="Field.TLabel").grid(
                row=0, column=column, sticky="w", padx=(0, 12)
            )
        self.subject = ttk.Combobox(form, state="readonly", width=18)
        self.teacher = ttk.Combobox(form, state="readonly", width=34)
        self.reason = ttk.Combobox(
            form,
            state="readonly",
            values=tuple(item.value for item in EmergencyReason),
            width=18,
        )
        self.reason.set(EmergencyReason.SICK_LEAVE.value)
        for column, widget in enumerate((self.subject, self.teacher, self.reason)):
            widget.grid(row=1, column=column, sticky="ew", padx=(0, 12))
            form.columnconfigure(column, weight=1)
        self.subject.bind("<<ComboboxSelected>>", self._subject_changed)
        self.teacher.bind("<<ComboboxSelected>>", self._selection_changed)
        self.reason.bind("<<ComboboxSelected>>", self._selection_changed)

        confirm_row = ttk.Frame(form, style="Card.TFrame")
        confirm_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(11, 0))
        ttk.Checkbutton(
            confirm_row,
            text="Mark this educator unavailable for the emergency timetable",
            variable=self.confirmed,
            command=self._selection_changed,
        ).pack(side="left")
        ttk.Button(
            confirm_row,
            text="Generate emergency preview",
            style="Warning.TButton",
            command=self.callbacks["generate"],
        ).pack(side="right")
        self.apply_button = ttk.Button(
            confirm_row,
            text="Apply emergency timetable",
            style="Danger.TButton",
            command=self.callbacks["apply"],
            state="disabled",
        )
        self.apply_button.pack(side="right", padx=(0, 8))
        ttk.Button(
            confirm_row,
            text="Plan with another educator",
            style="Secondary.TButton",
            command=self.callbacks["plan_another"],
        ).pack(side="right", padx=(0, 8))

        result = ttk.Frame(self, style="Card.TFrame", padding=10)
        result.pack(fill="both", expand=True, padx=6, pady=(3, 6))
        heading = ttk.Frame(result, style="Card.TFrame")
        heading.pack(fill="x", pady=(0, 6))
        ttk.Label(heading, text="Proposed emergency cover", style="Section.TLabel").pack(
            side="left"
        )
        self.result_count = ttk.Label(heading, text="0 affected days", style="Muted.TLabel")
        self.result_count.pack(side="right")

        self.change_tree = ttk.Treeview(
            result,
            columns=("day", "subject", "needed_at", "cover", "moved_from", "shortage"),
            show="headings",
            height=8,
            style="Compact.Treeview",
        )
        for column, label, width in (
            ("day", "Day", 90),
            ("subject", "Subject", 90),
            ("needed_at", "Cover needed at", 135),
            ("cover", "Educator reassigned", 180),
            ("moved_from", "Moved from", 125),
            ("shortage", "Reduced cover remains at", 165),
        ):
            self.change_tree.heading(column, text=label)
            self.change_tree.column(column, width=width)
        self.change_tree.pack(fill="both", expand=True)

        self.summary = tk.Text(
            result,
            height=7,
            wrap="word",
            relief="flat",
            bg="#F7F9FB",
            fg=COLORS["ink"],
            padx=8,
            pady=7,
            font=("Segoe UI", 9),
        )
        self.summary.pack(fill="x", pady=(8, 0))
        self.show_result((), "No emergency preview generated.", False)

    def set_options(self, teacher_subjects: dict[str, tuple[str, ...]]) -> None:
        selected_teacher = self.selected_teacher()
        selected_subject = self.subject.get()
        self._teacher_subjects = teacher_subjects
        subjects = sorted(
            {subject for values in teacher_subjects.values() for subject in values},
            key=str.casefold,
        )
        self.subject["values"] = (ALL_SUBJECTS, *subjects)
        self.subject.set(
            selected_subject if selected_subject in self.subject["values"] else ALL_SUBJECTS
        )
        self._filter_teachers(selected_teacher)

    def _filter_teachers(self, preferred_teacher: str = "") -> None:
        subject = self.subject.get()
        teachers = [
            teacher
            for teacher, subjects in self._teacher_subjects.items()
            if subject == ALL_SUBJECTS or subject in subjects
        ]
        labels = [teacher_label(teacher, self._teacher_subjects[teacher]) for teacher in teachers]
        self._teacher_by_label = dict(zip(labels, teachers))
        self.teacher["values"] = labels
        preferred_label = next(
            (label for label, teacher in self._teacher_by_label.items() if teacher == preferred_teacher),
            "",
        )
        self.teacher.set(preferred_label or (labels[0] if labels else ""))
        self.confirmed.set(False)

    def _subject_changed(self, _event=None) -> None:
        self._filter_teachers()
        self._selection_changed()

    def _selection_changed(self, _event=None) -> None:
        callback = self.callbacks.get("selection_changed")
        if callback is not None:
            callback()

    def selected_teacher(self) -> str:
        return self._teacher_by_label.get(self.teacher.get(), self.teacher.get())

    def selected_reason(self) -> EmergencyReason:
        try:
            return EmergencyReason(self.reason.get())
        except ValueError:
            return EmergencyReason.SICK_LEAVE

    def show_result(
        self,
        changes: tuple[EmergencyChange, ...],
        message: str,
        success: bool,
    ) -> None:
        self.change_tree.delete(*self.change_tree.get_children())
        for change in changes:
            self.change_tree.insert(
                "",
                "end",
                values=(
                    change.day,
                    change.subject,
                    change.emergency_school,
                    change.cover_teacher or "No reassignment",
                    change.moved_from or "—",
                    change.shortage_school,
                ),
            )
        count = len(changes)
        self.result_count.configure(
            text=f"{count} affected day{'s' if count != 1 else ''}"
        )
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("end", message)
        self.summary.configure(state="disabled")
        self.apply_button.configure(state="normal" if success else "disabled")

    def reset(self) -> None:
        self.confirmed.set(False)
        self.show_result((), "No emergency preview generated.", False)

    def prepare_another_teacher(self) -> None:
        """Clear the previous educator and return the planner to a blank form."""
        self.subject.set(ALL_SUBJECTS)
        self._filter_teachers()
        self.teacher.set("")
        self.reason.set(EmergencyReason.SICK_LEAVE.value)
        self.confirmed.set(False)
        self.show_result(
            (),
            "Previous selection cleared. Select and tick another unavailable educator.",
            False,
        )
