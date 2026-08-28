"""Staff directory and editable staffing notes."""

from __future__ import annotations

from tkinter import ttk

from ..domain import Timetable


class StaffTab(ttk.Frame):
    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, style="App.TFrame")
        self.callbacks = callbacks
        self._build()

    def _build(self) -> None:
        intro = ttk.Frame(self, style="Card.TFrame", padding=(14, 10))
        intro.pack(fill="x", padx=7, pady=(7, 4))
        ttk.Label(intro, text="Manage staff and staffing notes", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            intro,
            text=(
                "Add staff when the college grows, rename active teachers, remove departed "
                "staff, and keep the staffing updates shown on Overview current."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        content = ttk.Frame(self, style="App.TFrame")
        content.pack(fill="both", expand=True, padx=7, pady=(0, 7))
        content.columnconfigure(0, weight=1, uniform="staff")
        content.columnconfigure(1, weight=1, uniform="staff")
        content.rowconfigure(0, weight=1)

        teachers = ttk.Frame(content, style="Card.TFrame", padding=10)
        notes = ttk.Frame(content, style="Card.TFrame", padding=10)
        teachers.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        notes.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self._build_teachers(teachers)
        self._build_notes(notes)

    def _build_teachers(self, parent) -> None:
        heading = ttk.Frame(parent, style="Card.TFrame")
        heading.pack(fill="x")
        ttk.Label(heading, text="Active teacher directory", style="Section.TLabel").pack(
            side="left"
        )
        ttk.Button(
            heading,
            text="Add new teacher",
            style="Success.TButton",
            command=self.callbacks["add_teacher"],
        ).pack(side="right")
        form = ttk.Frame(parent, style="Card.TFrame")
        form.pack(fill="x", pady=(8, 8))
        ttk.Label(form, text="Teacher", style="Field.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="New name", style="Field.TLabel").grid(row=0, column=1, sticky="w")
        self.teacher = ttk.Combobox(form, state="readonly", width=26)
        self.new_name = ttk.Entry(form, width=28)
        self.teacher.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.new_name.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        actions = ttk.Frame(form, style="Card.TFrame")
        actions.grid(row=1, column=2, sticky="e")
        ttk.Button(
            actions,
            text="Rename",
            style="Primary.TButton",
            command=self.callbacks["rename_teacher"],
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Remove",
            style="Danger.TButton",
            command=self.callbacks["remove_teacher"],
        ).pack(side="left", padx=(6, 0))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self.teacher_tree = ttk.Treeview(
            parent,
            columns=("teacher", "subjects", "schools"),
            show="headings",
            style="Compact.Treeview",
            height=14,
        )
        for column, label, width in (
            ("teacher", "Teacher", 190),
            ("subjects", "Subject", 100),
            ("schools", "Current schools", 250),
        ):
            self.teacher_tree.heading(column, text=label)
            self.teacher_tree.column(column, width=width)
        self.teacher_tree.pack(fill="both", expand=True)
        self.teacher_tree.bind("<<TreeviewSelect>>", self._teacher_selected)

    def _build_notes(self, parent) -> None:
        ttk.Label(parent, text="Staffing updates", style="Section.TLabel").pack(anchor="w")
        form = ttk.Frame(parent, style="Card.TFrame")
        form.pack(fill="x", pady=(8, 8))
        for column, label in enumerate(("Person / post", "Status", "Note")):
            ttk.Label(form, text=label, style="Field.TLabel").grid(
                row=0, column=column, sticky="w"
            )
        self.note_name = ttk.Entry(form, width=20)
        self.note_status = ttk.Entry(form, width=18)
        self.note_text = ttk.Entry(form, width=34)
        for column, widget in enumerate((self.note_name, self.note_status, self.note_text)):
            widget.grid(row=1, column=column, sticky="ew", padx=(0, 8))
            form.columnconfigure(column, weight=1)
        actions = ttk.Frame(form, style="Card.TFrame")
        actions.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(
            actions,
            text="Add / update note",
            style="Primary.TButton",
            command=self.callbacks["save_note"],
        ).pack(side="left")
        ttk.Button(actions, text="Clear", command=self.clear_note_form).pack(
            side="left", padx=6
        )
        ttk.Button(
            actions,
            text="Delete selected",
            style="Danger.TButton",
            command=self.callbacks["delete_note"],
        ).pack(side="left")

        self.note_tree = ttk.Treeview(
            parent,
            columns=("name", "status", "note"),
            show="headings",
            style="Compact.Treeview",
            height=13,
        )
        for column, label, width in (
            ("name", "Person / post", 160),
            ("status", "Status", 110),
            ("note", "Note", 300),
        ):
            self.note_tree.heading(column, text=label)
            self.note_tree.column(column, width=width)
        self.note_tree.pack(fill="both", expand=True)
        self.note_tree.bind("<<TreeviewSelect>>", self._note_selected)

    def show(self, timetable: Timetable) -> None:
        selected_teacher = self.teacher.get()
        teachers = timetable.teachers
        self.teacher["values"] = teachers
        self.teacher.set(
            selected_teacher if selected_teacher in teachers else (teachers[0] if teachers else "")
        )
        self.teacher_tree.delete(*self.teacher_tree.get_children())
        for teacher in teachers:
            subjects = " / ".join(timetable.subjects_for_teacher(teacher))
            schools = sorted(
                {assignment.school for assignment in timetable.assignments_for(teacher=teacher)},
                key=str.casefold,
            )
            self.teacher_tree.insert("", "end", iid=teacher, values=(teacher, subjects, ", ".join(schools)))

        self.note_tree.delete(*self.note_tree.get_children())
        for index, note in enumerate(timetable.staff_notes):
            self.note_tree.insert("", "end", iid=str(index), values=(note.name, note.status, note.note))

    def _teacher_selected(self, _event=None) -> None:
        selected = self.teacher_tree.selection()
        if selected:
            self.teacher.set(selected[0])

    def _note_selected(self, _event=None) -> None:
        selected = self.note_tree.selection()
        if not selected:
            return
        values = self.note_tree.item(selected[0], "values")
        self.clear_note_form(clear_selection=False)
        for entry, value in zip((self.note_name, self.note_status, self.note_text), values):
            entry.insert(0, value)

    def selected_note_index(self) -> int | None:
        selected = self.note_tree.selection()
        return int(selected[0]) if selected else None

    def note_values(self) -> tuple[str, str, str]:
        return (
            self.note_name.get().strip(),
            self.note_status.get().strip(),
            self.note_text.get().strip(),
        )

    def clear_note_form(self, clear_selection: bool = True) -> None:
        for entry in (self.note_name, self.note_status, self.note_text):
            entry.delete(0, "end")
        if clear_selection:
            self.note_tree.selection_remove(self.note_tree.selection())

    def clear_teacher_form(self) -> None:
        self.new_name.delete(0, "end")
