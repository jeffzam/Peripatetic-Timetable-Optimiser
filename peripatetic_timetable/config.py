from pathlib import Path

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
PACKAGE_DIR = Path(__file__).resolve().parent
BASELINE_FILE = PACKAGE_DIR / "data" / "baseline.json"
DEFAULT_DATA_FILE = PACKAGE_DIR.parent / "user_data.json"
