# Peripatetic Timetable Optimiser

A desktop application for controlled rebalancing of peripatetic teacher timetables. The canonical timetable remains the starting point; changes are made through validated same-day, same-subject swaps.

## Features

- Batch removal and rebalancing across multiple teachers and days
- PE and PE/RSP compatibility
- One teacher, one school per day validation
- Teacher locks and day-specific school restrictions
- EXACT, MIN and MAX weekly school-frequency rules
- Preview before applying, plus original timetable restoration
- Teacher movement and Monday-to-Friday coverage audits
- CSV and formatted Excel export

## Project structure

- `peripatetic_timetable/scheduler.py` - rebalancing and validation engine
- `peripatetic_timetable/storage.py` - safe JSON persistence
- `peripatetic_timetable/audit.py` - movement and coverage reporting
- `peripatetic_timetable/exporters.py` - CSV and Excel output
- `peripatetic_timetable/ui.py` - Tkinter desktop interface
- `peripatetic_timetable/data/baseline.json` - canonical timetable
- `tests/` - scheduler regression tests

## Run

Python 3.10 or newer is required.

    python -m pip install -r requirements.txt
    python run.py

The app creates `user_data.json` in the working directory. This is ignored by Git because it contains local timetable changes.

## Test

    python -m unittest discover -s tests -v

## Data and privacy

Passwords, API keys, environment files, exports, and local working data are not tracked. Before using real personnel data, confirm that repository visibility and access controls match your organisation's privacy requirements.

## History

This clean v3 rewrite consolidates the prototype sequence through v2.6.1: timetable visualisation, PE/RSP planning, same-day conflict prevention, canonical baseline swaps, automatic batch rebalancing, restrictions, locks, weekly rules, auditing, and restoration.
