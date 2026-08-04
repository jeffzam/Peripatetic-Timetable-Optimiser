"""Transfer-planning screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..config import DAYS
from ..models import AppliedChange, TransferRequest, TransferType
from .theme import COLORS


ANY_SCHOOL = "Any suitable school"
ALL_SUBJECTS = "All subjects"


def teacher_label(teacher: str, subjects: tuple[str, ...]) -> str:
    """Build an informative name for teacher selection controls."""
    return f"{teacher} ({' / '.join(subjects)})" if subjects else teacher


class TransferTab(ttk.Frame):
    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, style="App.TFrame")
        self.callbacks = callbacks
        self.day_vars = {day: tk.BooleanVar() for day in DAYS}
        self._teacher_subjects: dict[str, tuple[str, ...]] = {}
        self._teacher_by_label: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        intro = ttk.Frame(self, style="Card.TFrame", padding=(12, 8))
        intro.pack(fill="x", padx=6, pady=(6, 3))
        ttk.Label(intro, text="Plan teacher transfers", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            intro,
            text=(
                "Build one or more requests, generate a safe preview, then review every "
                "swap before saving. The approved timetable is never changed directly."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        form = ttk.Frame(self, style="Card.TFrame", padding=10)
        form.pack(fill="x", padx=6, pady=3)
        labels = (
            ("Transfer type", 0),
            ("Subject", 1),
            ("Teacher", 2),
            ("Current school", 3),
            ("Preferred destination", 4),
        )
        for label, column in labels:
            ttk.Label(form, text=label, style="Field.TLabel").grid(
                row=0, column=column, sticky="w", padx=(0, 12)
            )
        self.transfer_type = ttk.Combobox(
            form,
            state="readonly",
            values=tuple(item.value for item in TransferType),
            width=18,
        )
        self.transfer_type.set(TransferType.PARTIAL.value)
        self.subject = ttk.Combobox(form, state="readonly", width=14)
        self.teacher = ttk.Combobox(form, state="readonly", width=30)
        self.source = ttk.Combobox(form, state="readonly", width=19)
        self.destination = ttk.Combobox(form, state="readonly", width=22)
        for column, widget in enumerate(
            (
                self.transfer_type,
                self.subject,
                self.teacher,
                self.source,
                self.destination,
            )
        ):
            widget.grid(row=1, column=column, sticky="ew", padx=(0, 12))
        self.teacher.bind("<<ComboboxSelected>>", lambda _event: self.callbacks["teacher_changed"]())
        self.subject.bind("<<ComboboxSelected>>", lambda _event: self._subject_changed())
        self.transfer_type.bind("<<ComboboxSelected>>", lambda _event: self._set_day_state())

        ttk.Label(form, text="Days for a partial transfer", style="Field.TLabel").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 3)
        )
        day_row = ttk.Frame(form, style="Card.TFrame")
        day_row.grid(row=3, column=0, columnspan=3, sticky="w")
        self.day_buttons = []
        for day in DAYS:
            button = ttk.Checkbutton(day_row, text=day[:3], variable=self.day_vars[day])
            button.pack(side="left", padx=(0, 9))
            self.day_buttons.append(button)

        ttk.Label(form, text="Additional excluded schools", style="Field.TLabel").grid(
            row=2, column=3, sticky="w", pady=(8, 3)
        )
        self.excluded = ttk.Entry(form, width=28)
        self.excluded.grid(row=3, column=3, sticky="ew", padx=(0, 12))
        ttk.Button(
            form,
            text="Add request",
            style="Primary.TButton",
            command=self.callbacks["add"],
        ).grid(row=3, column=4, sticky="e")
        for column in range(5):
            form.columnconfigure(column, weight=1)

        actions = ttk.Frame(self, style="App.TFrame")
        actions.pack(fill="x", padx=6, pady=3)
        ttk.Button(
            actions,
            text="Remove selected",
            style="Danger.TButton",
            command=self.callbacks["remove"],
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Clear requests",
            style="Secondary.TButton",
            command=self.callbacks["clear_requests"],
        ).pack(side="left", padx=7)
        ttk.Button(
            actions,
            text="Generate safe preview",
            style="Success.TButton",
            command=self.callbacks["generate"],
        ).pack(side="right")
        self.apply_button = ttk.Button(
            actions,
            text="Apply approved plan",
            style="Primary.TButton",
            command=self.callbacks["apply"],
            state="disabled",
        )
        self.apply_button.pack(side="right", padx=7)

        output = ttk.Frame(self, style="App.TFrame")
        output.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        output.columnconfigure(0, weight=1, uniform="transfer-output")
        output.columnconfigure(1, weight=1, uniform="transfer-output")
        output.rowconfigure(0, weight=1)
        queue = ttk.Frame(output, style="Card.TFrame", padding=(8, 6))
        result = ttk.Frame(output, style="Card.TFrame", padding=(8, 6))
        queue.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        result.grid(row=0, column=1, sticky="nsew", padx=(3, 0))

        queue_heading = ttk.Frame(queue, style="Card.TFrame")
        queue_heading.pack(fill="x", pady=(0, 5))
        ttk.Label(queue_heading, text="Transfer request queue", style="Section.TLabel").pack(
            side="left"
        )
        self.queue_count = ttk.Label(queue_heading, text="0 requests", style="Muted.TLabel")
        self.queue_count.pack(side="right")
        self.request_tree = ttk.Treeview(
            queue,
            columns=("type", "teacher", "source", "days", "destination", "excluded"),
            show="headings",
            height=8,
            style="Compact.Treeview",
        )
        for column, label, width in (
            ("type", "Type", 90),
            ("teacher", "Teacher", 125),
            ("source", "From", 75),
            ("days", "Days", 105),
            ("destination", "Destination", 115),
            ("excluded", "Excluded", 85),
        ):
            self.request_tree.heading(column, text=label)
            self.request_tree.column(column, width=width)
        self.request_tree.pack(fill="both", expand=True)

        result_heading = ttk.Frame(result, style="Card.TFrame")
        result_heading.pack(fill="x", pady=(0, 5))
        ttk.Label(result_heading, text="Proposed swaps", style="Section.TLabel").pack(
            side="left"
        )
        self.result_count = ttk.Label(result_heading, text="0 swaps", style="Muted.TLabel")
        self.result_count.pack(side="right")
        self.change_tree = ttk.Treeview(
            result,
            columns=("number", "teacher", "day", "source", "target", "swap", "score"),
            show="headings",
            height=6,
            style="Compact.Treeview",
        )
        for column, label, width in (
            ("number", "#", 38),
            ("teacher", "Teacher", 125),
            ("day", "Day", 70),
            ("source", "From", 72),
            ("target", "To", 72),
            ("swap", "Swap with", 125),
            ("score", "Fit", 48),
        ):
            self.change_tree.heading(column, text=label)
            self.change_tree.column(column, width=width)
        self.change_tree.pack(fill="x")
        self.summary = tk.Text(
            result,
            height=4,
            wrap="word",
            relief="flat",
            bg="#F7F9FB",
            fg=COLORS["ink"],
            padx=7,
            pady=6,
            font=("Segoe UI", 9),
        )
        self.summary.pack(fill="both", expand=True, pady=(8, 0))
        self.show_result((), "No preview generated.", False)

    def _set_day_state(self) -> None:
        is_full = self.transfer_type.get() == TransferType.FULL.value
        for button in self.day_buttons:
            button.configure(state="disabled" if is_full else "normal")
        if is_full:
            for value in self.day_vars.values():
                value.set(False)

    def set_options(
        self,
        teacher_subjects: dict[str, tuple[str, ...]],
        schools: list[str],
    ) -> None:
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
        self.destination["values"] = (ANY_SCHOOL, *schools)
        if not self.destination.get():
            self.destination.set(ANY_SCHOOL)

    def _subject_changed(self) -> None:
        self._filter_teachers()
        self.callbacks["teacher_changed"]()

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

    def selected_teacher(self) -> str:
        return self._teacher_by_label.get(self.teacher.get(), self.teacher.get())

    def set_source_options(self, schools: tuple[str, ...]) -> None:
        selected = self.source.get()
        self.source["values"] = schools
        self.source.set(selected if selected in schools else (schools[0] if schools else ""))

    def selected_days(self) -> tuple[str, ...]:
        return tuple(day for day, value in self.day_vars.items() if value.get())

    def excluded_schools(self) -> tuple[str, ...]:
        return tuple(
            value.strip()
            for value in self.excluded.get().replace(";", ",").split(",")
            if value.strip()
        )

    def reset_builder(self) -> None:
        self.transfer_type.set(TransferType.PARTIAL.value)
        self._set_day_state()
        for value in self.day_vars.values():
            value.set(False)
        self.excluded.delete(0, "end")

    def selected_request_index(self) -> int | None:
        selected = self.request_tree.selection()
        return self.request_tree.index(selected[0]) if selected else None

    def show_requests(self, requests: list[TransferRequest], timetable) -> None:
        self.request_tree.delete(*self.request_tree.get_children())
        for request in requests:
            days = (
                timetable.days_at_school(request.teacher, request.source_school)
                if request.transfer_type == TransferType.FULL
                else request.days
            )
            day_text = (
                "All weekdays"
                if tuple(days) == DAYS
                else ", ".join(day[:3] for day in days)
            )
            self.request_tree.insert(
                "",
                "end",
                values=(
                    request.transfer_type.value,
                    request.teacher,
                    request.source_school,
                    day_text,
                    request.preferred_school or ANY_SCHOOL,
                    ", ".join(request.excluded_schools) or "—",
                ),
            )
        count = len(requests)
        self.queue_count.configure(text=f"{count} request{'s' if count != 1 else ''}")
        children = self.request_tree.get_children()
        if children:
            self.request_tree.selection_set(children[-1])
            self.request_tree.see(children[-1])

    def show_result(
        self, changes: tuple[AppliedChange, ...], message: str, success: bool
    ) -> None:
        self.change_tree.delete(*self.change_tree.get_children())
        for item in changes:
            self.change_tree.insert(
                "",
                "end",
                values=(
                    item.request_number,
                    item.teacher,
                    item.day,
                    item.source_school,
                    item.target_school,
                    item.swap_teacher,
                    item.score,
                ),
            )
        count = len(changes)
        self.result_count.configure(text=f"{count} swap{'s' if count != 1 else ''}")
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("end", message)
        self.summary.configure(state="disabled")
        self.apply_button.configure(state="normal" if success else "disabled")


# Older imports continue to fail loudly at runtime only if external code used them.
RebalanceTab = TransferTab
