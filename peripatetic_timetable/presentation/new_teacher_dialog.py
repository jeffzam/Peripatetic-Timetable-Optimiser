"""Focused dialog for adding a new peripatetic teacher."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk

from ..audit import teacher_has_full_name
from ..config import DAYS
from ..domain import normalise


@dataclass(frozen=True)
class NewTeacherDetails:
    name: str
    subject: str
    placements: dict[str, str]


class NewTeacherDialog(tk.Toplevel):
    """Collect a full name, subject, and complete weekly placement."""

    def __init__(
        self,
        parent,
        schools: tuple[str, ...],
        subjects: tuple[str, ...],
        existing_teachers: tuple[str, ...],
    ) -> None:
        super().__init__(parent)
        self.result: NewTeacherDetails | None = None
        self.schools = schools
        self.existing_teachers = existing_teachers
        self.title("Add new teacher")
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.configure(background="#F2F5F7")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", self._submit)

        card = ttk.Frame(self, style="Card.TFrame", padding=20)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(card, text="Add a teacher to the college", style="Title.TLabel").grid(
            row=0, column=0, columnspan=5, sticky="w"
        )
        ttk.Label(
            card,
            text=(
                "This increases staffing. It does not replace or move another teacher. "
                "Choose where the new teacher will work on every weekday."
            ),
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(4, 14))

        ttk.Label(card, text="Full name", style="Field.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Label(card, text="Subject", style="Field.TLabel").grid(
            row=2, column=2, sticky="w", padx=(16, 0)
        )
        self.name = ttk.Entry(card, width=36)
        self.subject = ttk.Combobox(card, state="readonly", values=subjects, width=22)
        self.name.grid(row=3, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        self.subject.grid(row=3, column=2, columnspan=2, sticky="ew", padx=(16, 0))
        if subjects:
            self.subject.set(subjects[0])

        separator = ttk.Separator(card, orient="horizontal")
        separator.grid(row=4, column=0, columnspan=5, sticky="ew", pady=16)
        ttk.Label(card, text="Weekly school placement", style="Section.TLabel").grid(
            row=5, column=0, columnspan=5, sticky="w"
        )

        all_row = ttk.Frame(card, style="Card.TFrame")
        all_row.grid(row=6, column=0, columnspan=5, sticky="w", pady=(8, 12))
        ttk.Label(all_row, text="Same school all week", style="Field.TLabel").pack(
            side="left", padx=(0, 8)
        )
        self.all_school = ttk.Combobox(
            all_row, state="readonly", values=schools, width=24
        )
        self.all_school.pack(side="left")
        ttk.Button(
            all_row,
            text="Apply to all days",
            style="Secondary.TButton",
            command=self._apply_all_days,
        ).pack(side="left", padx=(8, 0))

        self.day_schools: dict[str, ttk.Combobox] = {}
        for column, day in enumerate(DAYS):
            ttk.Label(card, text=day, style="Field.TLabel").grid(
                row=7, column=column, sticky="w", padx=(0, 8)
            )
            selector = ttk.Combobox(card, state="readonly", values=schools, width=16)
            selector.grid(row=8, column=column, sticky="ew", padx=(0, 8))
            self.day_schools[day] = selector
            card.columnconfigure(column, weight=1)

        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.grid(row=9, column=0, columnspan=5, sticky="e", pady=(20, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left")
        ttk.Button(
            buttons,
            text="Add teacher",
            style="Success.TButton",
            command=self._submit,
        ).pack(side="left", padx=(8, 0))

        self.update_idletasks()
        owner = parent.winfo_toplevel()
        x = owner.winfo_rootx() + max(0, (owner.winfo_width() - self.winfo_width()) // 2)
        y = owner.winfo_rooty() + max(0, (owner.winfo_height() - self.winfo_height()) // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.name.focus_set()

    def _apply_all_days(self) -> None:
        school = self.all_school.get()
        if not school:
            messagebox.showwarning(
                "Choose a school",
                "Select the school to use for all five days.",
                parent=self,
            )
            return
        for selector in self.day_schools.values():
            selector.set(school)

    def _submit(self, _event=None) -> None:
        name = self.name.get().strip()
        subject = self.subject.get().strip()
        placements = {day: selector.get() for day, selector in self.day_schools.items()}
        if not teacher_has_full_name(name):
            messagebox.showwarning(
                "Full name required",
                "Enter both the teacher's first name and surname.",
                parent=self,
            )
            return
        if any(normalise(teacher) == normalise(name) for teacher in self.existing_teachers):
            messagebox.showwarning(
                "Teacher already exists",
                "That teacher is already in the active directory.",
                parent=self,
            )
            return
        if not subject:
            messagebox.showwarning(
                "Subject required", "Choose the teacher's subject.", parent=self
            )
            return
        missing_days = [day for day in DAYS if not placements[day]]
        if missing_days:
            messagebox.showwarning(
                "Complete the week",
                "Choose a school for " + ", ".join(missing_days) + ".",
                parent=self,
            )
            return
        self.result = NewTeacherDetails(name, subject, placements)
        self.destroy()


def ask_new_teacher(
    parent,
    schools: tuple[str, ...],
    subjects: tuple[str, ...],
    existing_teachers: tuple[str, ...],
) -> NewTeacherDetails | None:
    dialog = NewTeacherDialog(parent, schools, subjects, existing_teachers)
    parent.wait_window(dialog)
    return dialog.result
