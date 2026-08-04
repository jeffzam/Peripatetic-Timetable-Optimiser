# Peripatetic Timetable Planner

A clean Python desktop application for managing St Nicholas College's peripatetic
teacher timetable and testing full or partial transfers without changing the
approved starting timetable.

The canonical data was verified against **Time table 29th July .doc** for the
2026/2027 scholastic year. The application always works on a separate local copy.

## What the first clean version does

- Presents the six-school timetable in a clear school-by-day grid.
- Audits whether every active teacher has a school on every weekday.
- Detects teachers assigned to more than one school on the same day.
- Plans **full transfers** for every day a teacher serves at a selected school.
- Plans **partial transfers** for selected days only.
- Keeps one destination school for each complete transfer request.
- Finds subject-compatible counterpart teachers and explains every proposed swap.
- Treats PE and PE/RSP as compatible for transfer-cover purposes.
- Checks PE/RSP educator-day capacity from school class totals.
- Supports multi-day or all-week teacher locks, excluded schools, and weekly frequency rules.
- Generates a preview before any change can be saved.
- Exports the timetable, teacher movement, audit, and history to Excel or CSV.

Alisichia's source allocation is Baħrija on Tuesday, Wednesday and Friday, and Rabat
on Monday and Thursday.

## Run

Python 3.10 or newer is required. Its optional **Tcl/Tk and IDLE** component must
also be installed for the desktop interface.

```text
python -m pip install -r requirements.txt
python run.py
```

The working copy is stored as `user_data.json`. The protected starting data remains
in `peripatetic_timetable/data/baseline.json`.

## Code structure

- `domain.py` — timetable data and structural validation
- `policy.py` — PE/RSP workload and subject-compatibility policy
- `audit.py` — explainable coverage and capacity checks
- `optimizer.py` — full and partial transfer search
- `repository.py` — protected baseline and atomic local saving
- `reports.py` and `exports.py` — operational reports and exports
- `presentation/` — independent desktop screens and visual styling

## Tests

```text
python -m unittest discover -s tests -v
```

Personnel data stays local unless a user deliberately publishes it. Local working
copies, backups, exports, credentials, executables, and archives are ignored by Git.
