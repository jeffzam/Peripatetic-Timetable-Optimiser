# Peripatetic Timetable Planner

A clean Python desktop application for managing St Nicholas College's peripatetic
teacher timetable and testing full or partial transfers without changing the
approved starting timetable.

The canonical data was verified against **Time table 29th July .doc** for the
2026/2027 scholastic year. The application always works on a separate local copy.

## What version 2.1.1 does

- Presents the six-school timetable in a clear school-by-day grid.
- Fits every school and weekday on screen, gives busy schools more row space, and colour-codes subjects.
- Audits whether every active teacher has a school on every weekday.
- Flags incomplete teacher names and prompts for a first name and surname.
- Detects teachers assigned to more than one school on the same day.
- Plans **full transfers** for every day a teacher serves at a selected school.
- Plans **partial transfers** for selected days only.
- Keeps one destination school for each complete transfer request.
- Finds subject-compatible counterpart teachers and explains every proposed swap.
- Treats PE and PE/RSP as compatible for transfer-cover purposes.
- Uses PE/RSP as the single official label for all physical-education teachers.
- Checks PE/RSP educator-day capacity from school class totals.
- Supports multi-day or all-week teacher locks, excluded schools, and weekly frequency rules.
- Filters the transfer teacher list by subject and displays each teacher's subject beside their name.
- Generates a preview before any change can be saved.
- Saves a dated local restore point whenever an approved transfer plan is applied.
- Restores the original baseline or any dated approval without discarding the timetable being replaced.
- Adds, edits, and deletes staffing updates from a dedicated Staff page.
- Renames teachers consistently across placements and rules, or removes departed teachers safely.
- Wraps staffing notes on Overview so the complete update remains readable.
- Exports the timetable, teacher movement, audit, and history to Excel or CSV.

Alisichia's source allocation is Baħrija on Tuesday, Wednesday and Friday, and Rabat
on Monday and Thursday.

## Run

Python 3.10 or newer is required. Its optional **Tcl/Tk and IDLE** component must
also be installed for the desktop interface.

For the simplest Windows start, open the project folder and double-click
`START PLANNER.bat`. On the first start it automatically installs the declared
Excel-export support if it is missing.

```text
python -m pip install -r requirements.txt
python run.py
```

The working copy is stored as `user_data.json`, while dated restore points are kept
in the local `user_data_history` folder. The protected starting data remains in
`peripatetic_timetable/data/baseline.json`.

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
