"""Transfer-planning screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..config import DAYS
from ..models import AppliedChange, TransferRequest, TransferType
from .theme import COLORS


ANY_SCHOOL = "Any suitable school"


class TransferTab(ttk.Frame):
    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, style="App.TFrame")
        self.callbacks = callbacks
        self.day_vars = {day: tk.BooleanVar() for day in DAYS}
        self._build()

    def _build(self) -> None:
        intro = ttk.Frame(self, style="Card.TFrame", padding=(18, 14))
        intro.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(intro, text="Plan teacher transfers", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            intro,
            text=(
                "Build one or more requests, generate a safe preview, then review every "
                "swap before saving. The approved timetable is never changed directly."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        form = ttk.Frame(self, style="Card.TFrame", padding=16)
        form.pack(fill="x", padx=10, pady=6)
        labels = (
            ("Transfer type", 0),
            ("Teacher", 1),
            ("Current school", 2),
            ("Preferred destination", 3),
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
        self.teacher = ttk.Combobox(form, state="readonly", width=25)
        self.source = ttk.Combobox(form, state="readonly", width=19)
        self.destination = ttk.Combobox(form, state="readonly", width=22)
        for column, widget in enumerate(
            (self.transfer_type, self.teacher, self.source, self.destination)
        ):
            widget.grid(row=1, column=column, sticky="ew", padx=(0, 12))
        self.teacher.bind("<<ComboboxSelected>>", lambda _event: self.callbacks["teacher_changed"]())
        self.transfer_type.bind("<<ComboboxSelected>>", lambda _event: self._set_day_state())

        ttk.Label(form, text="Days for a partial transfer", style="Field.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(14, 4)
        )
        day_row = ttk.Frame(form, style="Card.TFrame")
        day_row.grid(row=3, column=0, columnspan=2, sticky="w")
        self.day_buttons = []
        for day in DAYS:
            button = ttk.Checkbutton(day_row, text=day[:3], variable=self.day_vars[day])
            button.pack(side="left", padx=(0, 9))
            self.day_buttons.append(button)

        ttk.Label(form, text="Additional excluded schools", style="Field.TLabel").grid(
            row=2, column=2, sticky="w", pady=(14, 4)
        )
        self.excluded = ttk.Entry(form, width=28)
        self.excluded.grid(row=3, column=2, sticky="ew", padx=(0, 12))
        ttk.Button(
            form,
            text="Add request",
            style="Primary.TButton",
            command=self.callbacks["add"],
        ).grid(row=3, column=3, sticky="e")
        for column in range(4):
            form.columnconfigure(column, weight=1)

        actions = ttk.Frame(self, style="App.TFrame")
        actions.pack(fill="x", padx=10, pady=6)
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

        split = ttk.Panedwindow(self, orient="vertical")
        split.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        queue = ttk.Frame(split, style="Card.TFrame", padding=12)
        result = ttk.Frame(split, style="Card.TFrame", padding=12)
        split.add(queue, weight=1)
        split.add(result, weight=2)
        ttk.Label(queue, text="Transfer request queue", style="Section.TLabel").pack(
            anchor="w", pady=(0, 7)
        )
        self.request_tree = ttk.Treeview(
            queue,
            columns=("type", "teacher", "source", "days", "destination", "excluded"),
            show="headings",
            height=5,
        )
        for column, label, width in (
            ("type", "Type", 125),
            ("teacher", "Teacher", 210),
            ("source", "From", 135),
            ("days", "Days", 220),
            ("destination", "Preferred destination", 170),
            ("excluded", "Excluded", 220),
        ):
            self.request_tree.heading(column, text=label)
            self.request_tree.column(column, width=width)
        self.request_tree.pack(fill="both", expand=True)

        ttk.Label(result, text="Proposed swaps", style="Section.TLabel").pack(
            anchor="w", pady=(0, 7)
        )
        self.change_tree = ttk.Treeview(
            result,
            columns=("number", "teacher", "day", "source", "target", "swap", "score"),
            show="headings",
            height=5,
        )
        for column, label, width in (
            ("number", "Request", 70),
            ("teacher", "Teacher", 190),
            ("day", "Day", 100),
            ("source", "From", 125),
            ("target", "To", 125),
            ("swap", "Swap with", 190),
            ("score", "Fit score", 80),
        ):
            self.change_tree.heading(column, text=label)
            self.change_tree.column(column, width=width)
        self.change_tree.pack(fill="x")
        self.summary = tk.Text(
            result,
            height=6,
            wrap="word",
            relief="flat",
            bg="#F7F9FB",
            fg=COLORS["ink"],
            padx=11,
            pady=9,
            font=("Segoe UI", 10),
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

    def set_options(self, teachers: list[str], schools: list[str]) -> None:
        self.teacher["values"] = teachers
        self.destination["values"] = (ANY_SCHOOL, *schools)
        if not self.destination.get():
            self.destination.set(ANY_SCHOOL)

    def set_source_options(self, schools: tuple[str, ...]) -> None:
        self.source["values"] = schools
        self.source.set(schools[0] if schools else "")

    def selected_days(self) -> tuple[str, ...]:
        return tuple(day for day, value in self.day_vars.items() if value.get())

    def excluded_schools(self) -> tuple[str, ...]:
        return tuple(
            value.strip()
            for value in self.excluded.get().replace(";", ",").split(",")
            if value.strip()
        )

    def reset_builder(self) -> None:
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
            self.request_tree.insert(
                "",
                "end",
                values=(
                    request.transfer_type.value,
                    request.teacher,
                    request.source_school,
                    ", ".join(day[:3] for day in days),
                    request.preferred_school or ANY_SCHOOL,
                    ", ".join(request.excluded_schools) or "—",
                ),
            )

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
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("end", message)
        self.summary.configure(state="disabled")
        self.apply_button.configure(state="normal" if success else "disabled")


# Older imports continue to fail loudly at runtime only if external code used them.
RebalanceTab = TransferTab
