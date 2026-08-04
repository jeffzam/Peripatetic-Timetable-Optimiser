import copy
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .audit import coverage_audit, teacher_movement
from .config import APP_TITLE, DAYS
from .exporters import export_csv, export_excel
from .models import RebalanceRequest
from .scheduler import RebalanceEngine
from .storage import TimetableStore

class TimetableApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1500x850")
        self.minsize(1100, 650)
        self.store = TimetableStore()
        self.preview = None
        self.requests = []
        self.last_changes = ()
        self._build()
        self.refresh()

    @property
    def active_data(self):
        return self.preview or self.store.data

    def _build(self):
        header = tk.Frame(self, bg="#17324d")
        header.pack(fill="x")
        tk.Label(header, text=APP_TITLE, bg="#17324d", fg="white",
                 font=("Segoe UI", 18, "bold")).pack(side="left", padx=16, pady=14)
        for label, command, colour in [
            ("RESTORE ORIGINAL", self.restore, "#ef6c00"),
            ("EXPORT EXCEL", self.save_excel, "#1b5e20"),
            ("EXPORT CSV", self.save_csv, "#1565c0"),
            ("CLEAR PREVIEW", self.clear_preview, "#455a64")]:
            tk.Button(header, text=label, command=command, bg=colour, fg="white",
                      font=("Segoe UI", 10, "bold")).pack(side="right", padx=5, pady=10)
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self._build_timetable()
        self._build_requests()
        self._build_constraints()
        self._build_report("Teacher Movement", "movement")
        self._build_report("Coverage Audit", "audit")
        self._build_report("Change Log", "log")

    def _tab(self, title):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text=title)
        return tab

    def _build_timetable(self):
        tab = self._tab("Live Timetable")
        columns = ("school", "classes", *DAYS)
        self.timetable = ttk.Treeview(tab, columns=columns, show="headings")
        for column in columns:
            self.timetable.heading(column, text=column.title())
            self.timetable.column(column, width=130 if column in ("school", "classes") else 220)
        self.timetable.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_requests(self):
        tab = self._tab("Batch Rebalance")
        form = ttk.Frame(tab)
        form.pack(fill="x", padx=10, pady=8)
        ttk.Label(form, text="Teacher").grid(row=0, column=0, padx=4)
        self.req_teacher = ttk.Combobox(form, width=28, state="readonly")
        self.req_teacher.grid(row=0, column=1, padx=4)
        ttk.Label(form, text="Excluded schools").grid(row=0, column=2, padx=4)
        self.req_excluded = ttk.Entry(form, width=28)
        self.req_excluded.grid(row=0, column=3, padx=4)
        self.day_vars = {day: tk.BooleanVar() for day in DAYS}
        for index, day in enumerate(DAYS):
            ttk.Checkbutton(form, text=day, variable=self.day_vars[day]).grid(row=1, column=index, padx=6)
        ttk.Button(form, text="Add request", command=self.add_request).grid(row=0, column=4, padx=6)
        ttk.Button(form, text="Remove selected", command=self.remove_request).grid(row=0, column=5, padx=6)
        ttk.Button(form, text="Generate preview", command=self.solve).grid(row=1, column=5, padx=6)
        ttk.Button(form, text="Apply batch", command=self.apply).grid(row=1, column=6, padx=6)
        self.request_tree = ttk.Treeview(tab, columns=("teacher", "day", "excluded"), show="headings", height=7)
        for column in ("teacher", "day", "excluded"):
            self.request_tree.heading(column, text=column.title())
        self.request_tree.pack(fill="x", padx=10, pady=5)
        self.analysis = tk.Text(tab, height=14, wrap="word")
        self.analysis.pack(fill="both", expand=True, padx=10, pady=8)

    def _build_constraints(self):
        tab = self._tab("Constraints")
        self.constraint_kind = ttk.Combobox(tab, values=("Restriction", "Lock", "Weekly rule"), state="readonly")
        self.constraint_kind.set("Restriction")
        self.constraint_teacher = ttk.Combobox(tab, state="readonly", width=26)
        self.constraint_school = ttk.Combobox(tab, state="readonly", width=18)
        self.constraint_day = ttk.Combobox(tab, values=("ALL", *DAYS), state="readonly", width=12)
        self.constraint_day.set("ALL")
        self.constraint_rule = ttk.Combobox(tab, values=("EXACT", "MIN", "MAX"), state="readonly", width=10)
        self.constraint_rule.set("EXACT")
        self.constraint_times = ttk.Entry(tab, width=7)
        widgets = [("Type", self.constraint_kind), ("Teacher", self.constraint_teacher),
                   ("School", self.constraint_school), ("Day", self.constraint_day),
                   ("Rule", self.constraint_rule), ("Times", self.constraint_times)]
        for index, (label, widget) in enumerate(widgets):
            ttk.Label(tab, text=label).grid(row=0, column=index, padx=5, pady=8)
            widget.grid(row=1, column=index, padx=5)
        ttk.Button(tab, text="Add", command=self.add_constraint).grid(row=1, column=6, padx=6)
        ttk.Button(tab, text="Delete selected", command=self.delete_constraint).grid(row=1, column=7, padx=6)
        self.constraint_tree = ttk.Treeview(tab, columns=("type", "teacher", "school", "day_rule", "times"), show="headings")
        for column in ("type", "teacher", "school", "day_rule", "times"):
            self.constraint_tree.heading(column, text=column.replace("_", " ").title())
        self.constraint_tree.grid(row=2, column=0, columnspan=8, sticky="nsew", padx=10, pady=10)
        tab.rowconfigure(2, weight=1)
        tab.columnconfigure(7, weight=1)

    def _build_report(self, title, name):
        tab = self._tab(title)
        text = tk.Text(tab, wrap="none", font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=8, pady=8)
        setattr(self, f"{name}_text", text)

    def teachers(self):
        return sorted({row["teacher"] for row in self.store.data["assignments"]})

    def schools(self):
        return [row["name"] for row in self.store.data["schools"]]

    def add_request(self):
        teacher = self.req_teacher.get()
        days = [day for day, value in self.day_vars.items() if value.get()]
        if not teacher or not days:
            messagebox.showwarning("Missing selection", "Choose a teacher and at least one day.")
            return
        excluded = tuple(value.strip() for value in self.req_excluded.get().replace(";", ",").split(",") if value.strip())
        for day in days:
            request = RebalanceRequest(teacher, day, excluded)
            if request not in self.requests:
                self.requests.append(request)
        for value in self.day_vars.values():
            value.set(False)
        self.refresh_requests()

    def remove_request(self):
        selection = self.request_tree.selection()
        if selection:
            self.requests.pop(self.request_tree.index(selection[0]))
            self.refresh_requests()

    def solve(self):
        result = RebalanceEngine(self.store.data).solve_batch(self.requests)
        self.analysis.delete("1.0", "end")
        if not result.succeeded:
            self.preview, self.last_changes = None, ()
            self.analysis.insert("end", "BATCH BLOCKED\n\n" + result.error)
        else:
            self.preview, self.last_changes = result.data, result.changes
            self.analysis.insert("end", "GENERATED BATCH\n\n" + "\n".join(change.note for change in result.changes))
        self.refresh_reports()
        self.refresh_timetable()

    def apply(self):
        if not self.preview:
            return
        self.store.data = self.preview
        version = f"3.{len(self.store.data.get('change_log', []))}"
        self.store.data.setdefault("change_log", []).append({"version": version, "note": " | ".join(c.note for c in self.last_changes)})
        self.store.save()
        self.preview, self.last_changes, self.requests = None, (), []
        self.refresh()
        messagebox.showinfo("Applied", f"Batch saved as v{version}.")

    def add_constraint(self):
        kind, teacher, school = self.constraint_kind.get(), self.constraint_teacher.get(), self.constraint_school.get()
        if not teacher or not school:
            return
        if kind == "Restriction":
            self.store.data.setdefault("teacher_restrictions", []).append({"teacher": teacher, "school": school, "days": self.constraint_day.get(), "reason": ""})
        elif kind == "Lock" and self.constraint_day.get() in DAYS:
            self.store.data.setdefault("locks", []).append({"teacher": teacher, "school": school, "day": self.constraint_day.get()})
        elif kind == "Weekly rule" and self.constraint_times.get().isdigit():
            self.store.data.setdefault("weekly_rules", []).append({"teacher": teacher, "school": school, "type": self.constraint_rule.get(), "times": int(self.constraint_times.get())})
        else:
            return
        self.store.save()
        self.refresh_constraints()

    def delete_constraint(self):
        selection = self.constraint_tree.selection()
        if not selection:
            return
        item = self.constraint_tree.item(selection[0], "values")
        kind, index = item[0].split(" #")
        field = {"Restriction": "teacher_restrictions", "Lock": "locks", "Weekly rule": "weekly_rules"}[kind]
        self.store.data[field].pop(int(index))
        self.store.save()
        self.refresh_constraints()

    def refresh_timetable(self):
        self.timetable.delete(*self.timetable.get_children())
        for school in self.active_data["schools"]:
            values = [school["name"], school["breakdown"]]
            values += [" | ".join(f"{row['subject']} - {row['teacher']}" for row in self.active_data["assignments"] if row["school"] == school["name"] and row["day"] == day) for day in DAYS]
            self.timetable.insert("", "end", values=values)

    def refresh_requests(self):
        self.request_tree.delete(*self.request_tree.get_children())
        for row in self.requests:
            self.request_tree.insert("", "end", values=(row.teacher, row.day, ", ".join(row.excluded_schools)))

    def refresh_constraints(self):
        self.constraint_tree.delete(*self.constraint_tree.get_children())
        for label, field in (("Restriction", "teacher_restrictions"), ("Lock", "locks"), ("Weekly rule", "weekly_rules")):
            for index, row in enumerate(self.store.data.get(field, [])):
                self.constraint_tree.insert("", "end", values=(f"{label} #{index}", row["teacher"], row["school"], row.get("days", row.get("day", row.get("type", ""))), row.get("times", "")))

    def refresh_reports(self):
        movement = teacher_movement(self.active_data)
        self.movement_text.delete("1.0", "end")
        for teacher, days in movement.items():
            self.movement_text.insert("end", teacher + ": " + " | ".join(f"{day}: {days[day] or '-'}" for day in DAYS) + "\n")
        self.audit_text.delete("1.0", "end")
        for row in coverage_audit(self.active_data):
            self.audit_text.insert("end", f"{row['teacher']}: {row['status']} | Missing: {', '.join(row['missing_days']) or '-'}\n")
        self.log_text.delete("1.0", "end")
        for row in self.store.data.get("change_log", []):
            self.log_text.insert("end", f"{row.get('version', '')} - {row.get('note', '')}\n")

    def refresh(self):
        values, schools = self.teachers(), self.schools()
        self.req_teacher["values"] = values
        self.constraint_teacher["values"] = values
        self.constraint_school["values"] = schools
        self.refresh_timetable()
        self.refresh_requests()
        self.refresh_constraints()
        self.refresh_reports()

    def clear_preview(self):
        self.preview, self.last_changes = None, ()
        self.refresh_timetable()
        self.refresh_reports()

    def restore(self):
        if messagebox.askyesno("Restore", "Replace all local changes with the original timetable?"):
            self.store.restore_baseline()
            self.preview, self.requests, self.last_changes = None, [], ()
            self.refresh()

    def save_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            export_csv(self.active_data, path)

    def save_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            try:
                export_excel(self.active_data, path)
            except ImportError:
                messagebox.showerror("Missing dependency", "Install dependencies from requirements.txt first.")
