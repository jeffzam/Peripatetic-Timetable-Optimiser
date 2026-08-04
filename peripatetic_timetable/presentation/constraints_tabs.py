import tkinter as tk
from tkinter import ttk

from ..config import DAYS

class _ManagedTab(ttk.Frame):
    def __init__(self, parent, add_callback, delete_callback):
        super().__init__(parent, style="App.TFrame")
        self.add_callback = add_callback
        self.delete_callback = delete_callback

    def selected_index(self) -> int | None:
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def _buttons(self, parent):
        ttk.Button(parent, text="Add", style="Primary.TButton", command=self.add_callback).pack(side="left")
        ttk.Button(parent, text="Delete selected", style="Danger.TButton", command=self.delete_callback).pack(side="left", padx=6)

class RestrictionsTab(_ManagedTab):
    def __init__(self, parent, add_callback, delete_callback):
        super().__init__(parent, add_callback, delete_callback)
        self.day_vars = {day: tk.BooleanVar(value=True) for day in DAYS}
        form = ttk.Frame(self, style="Card.TFrame", padding=14)
        form.pack(fill="x", padx=8, pady=8)
        ttk.Label(form, text="Teacher restrictions", style="Title.TLabel").grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))
        ttk.Label(form, text="Teacher", style="Card.TLabel").grid(row=1, column=0, sticky="w")
        ttk.Label(form, text="Cannot visit", style="Card.TLabel").grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Reason", style="Card.TLabel").grid(row=1, column=2, sticky="w")
        self.teacher, self.school = ttk.Combobox(form, state="readonly", width=25), ttk.Combobox(form, state="readonly", width=18)
        self.reason = ttk.Entry(form, width=34)
        self.teacher.grid(row=2, column=0, padx=(0, 10)); self.school.grid(row=2, column=1, padx=(0, 10)); self.reason.grid(row=2, column=2, padx=(0, 10))
        days = ttk.Frame(form, style="Card.TFrame"); days.grid(row=1, column=3, rowspan=2, padx=8)
        ttk.Label(days, text="Applies on", style="Card.TLabel").pack(anchor="w")
        for day in DAYS:
            ttk.Checkbutton(days, text=day[:3], variable=self.day_vars[day]).pack(side="left")
        buttons = ttk.Frame(form, style="Card.TFrame"); buttons.grid(row=2, column=4); self._buttons(buttons)
        self.tree = ttk.Treeview(self, columns=("teacher", "school", "days", "reason"), show="headings")
        for column, label, width in (("teacher", "Teacher", 240), ("school", "Excluded school", 170), ("days", "Days", 270), ("reason", "Reason", 420)):
            self.tree.heading(column, text=label); self.tree.column(column, width=width)
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def values(self):
        return self.teacher.get(), self.school.get(), tuple(day for day, value in self.day_vars.items() if value.get()), self.reason.get().strip()

    def show(self, rows):
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(rows):
            self.tree.insert("", "end", iid=str(index), values=(row.teacher, row.school, ", ".join(row.days), row.reason or "—"))

class LocksTab(_ManagedTab):
    def __init__(self, parent, add_callback, delete_callback):
        super().__init__(parent, add_callback, delete_callback)
        self.day_vars = {day: tk.BooleanVar(value=False) for day in DAYS}
        self.all_days = tk.BooleanVar(value=False)
        form = ttk.Frame(self, style="Card.TFrame", padding=14); form.pack(fill="x", padx=8, pady=8)
        ttk.Label(form, text="Teacher locks", style="Title.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        ttk.Label(
            form,
            text="Select one or more days. Each day is locked to the teacher's current school.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 12))
        ttk.Label(form, text="Teacher", style="Field.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Label(form, text="Days to lock", style="Field.TLabel").grid(row=2, column=1, sticky="w")
        self.teacher = ttk.Combobox(form, state="readonly", width=25)
        self.teacher.grid(row=3, column=0, padx=(0, 18), sticky="w")
        day_panel = ttk.Frame(form, style="Card.TFrame")
        day_panel.grid(row=3, column=1, padx=(0, 18), sticky="w")
        ttk.Checkbutton(
            day_panel,
            text="All weekdays",
            variable=self.all_days,
            command=self._toggle_all_days,
        ).pack(side="left", padx=(0, 12))
        for day in DAYS:
            ttk.Checkbutton(
                day_panel,
                text=day[:3],
                variable=self.day_vars[day],
                command=self._sync_all_days,
            ).pack(side="left", padx=(0, 7))
        buttons = ttk.Frame(form, style="Card.TFrame"); buttons.grid(row=3, column=2, sticky="e"); self._buttons(buttons)
        form.columnconfigure(1, weight=1)
        self.tree = ttk.Treeview(self, columns=("teacher", "day", "school"), show="headings")
        for column, label, width in (("teacher", "Teacher", 260), ("day", "Day", 160), ("school", "Locked school", 220)):
            self.tree.heading(column, text=label); self.tree.column(column, width=width)
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _toggle_all_days(self):
        selected = self.all_days.get()
        for value in self.day_vars.values():
            value.set(selected)

    def _sync_all_days(self):
        self.all_days.set(all(value.get() for value in self.day_vars.values()))

    def values(self):
        return self.teacher.get(), tuple(
            day for day, value in self.day_vars.items() if value.get()
        )

    def clear_days(self):
        self.all_days.set(False)
        for value in self.day_vars.values():
            value.set(False)

    def show(self, rows):
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(rows):
            self.tree.insert("", "end", iid=str(index), values=(row.teacher, row.day, row.school))

class WeeklyRulesTab(_ManagedTab):
    def __init__(self, parent, add_callback, delete_callback):
        super().__init__(parent, add_callback, delete_callback)
        form = ttk.Frame(self, style="Card.TFrame", padding=14); form.pack(fill="x", padx=8, pady=8)
        ttk.Label(form, text="Weekly school-frequency rules", style="Title.TLabel").grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))
        self.teacher, self.school = ttk.Combobox(form, state="readonly", width=25), ttk.Combobox(form, state="readonly", width=18)
        self.kind = ttk.Combobox(form, state="readonly", values=("EXACT", "MIN", "MAX"), width=12); self.kind.set("EXACT")
        self.times = ttk.Spinbox(form, from_=0, to=5, width=7)
        for column, (label, widget) in enumerate((("Teacher", self.teacher), ("School", self.school), ("Rule", self.kind), ("Times per week", self.times))):
            ttk.Label(form, text=label, style="Card.TLabel").grid(row=1, column=column, sticky="w")
            widget.grid(row=2, column=column, padx=(0, 10))
        buttons = ttk.Frame(form, style="Card.TFrame"); buttons.grid(row=2, column=4); self._buttons(buttons)
        self.tree = ttk.Treeview(self, columns=("teacher", "school", "kind", "times"), show="headings")
        for column, label, width in (("teacher", "Teacher", 260), ("school", "School", 190), ("kind", "Rule", 130), ("times", "Times per week", 140)):
            self.tree.heading(column, text=label); self.tree.column(column, width=width)
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def values(self):
        return self.teacher.get(), self.school.get(), self.kind.get(), self.times.get()

    def show(self, rows):
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(rows):
            self.tree.insert("", "end", iid=str(index), values=(row.teacher, row.school, row.kind, row.times))

def set_constraint_options(tabs, teachers: list[str], schools: list[str]):
    for tab in tabs:
        tab.teacher["values"] = teachers
        if hasattr(tab, "school"):
            tab.school["values"] = schools
