"""
persistence.py — JSON-based persistence layer.

Saves and loads all students and courses to/from a JSON file.
To swap storage (e.g. SQLite), only this file needs changing.

Error handling:
- File missing   → returns empty dicts, informs user
- Corrupt JSON   → returns empty dicts, informs user, does not crash
- Bad record     → skips that record, loads the rest
"""

import json
import logging
from pathlib import Path

from university.models.course import Course
from university.models.student import Student

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "university_data.json"


def save_data(students: dict, courses: dict) -> None:
    """Serialise all students and courses to JSON."""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "students": {sid: s.to_dict() for sid, s in students.items()},
        "courses": {code: c.to_dict() for code, c in courses.items()},
    }

    with DATA_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    logger.info("Saved %d students and %d courses", len(students), len(courses))
    print(f"[✓] Saved {len(students)} student(s) and {len(courses)} course(s) to:")
    print(f"    {DATA_PATH}")


def load_data() -> tuple[dict, dict]:
    """
    Load students and courses from JSON.
    Returns empty dicts if file is missing or unreadable.
    """
    if not DATA_PATH.exists():
        print(f"[!] No saved data found at:\n    {DATA_PATH}")
        print("    Starting with an empty system.")
        return {}, {}

    try:
        with DATA_PATH.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except json.JSONDecodeError as exc:
        print("[✗] Data file is corrupt and could not be loaded.")
        print(f"    Error: {exc}")
        print("    Starting with an empty system. Your file has NOT been deleted.")
        return {}, {}
    except OSError as exc:
        print(f"[✗] Could not read data file: {exc}")
        return {}, {}

    students: dict[str, Student] = {}
    for sid, data in payload.get("students", {}).items():
        try:
            students[sid] = Student.from_dict(data)
        except (KeyError, ValueError, TypeError) as exc:
            print(f"  [!] Skipped corrupt student record '{sid}': {exc}")

    courses: dict[str, Course] = {}
    for code, data in payload.get("courses", {}).items():
        try:
            courses[code] = Course.from_dict(data)
        except (KeyError, ValueError, TypeError) as exc:
            print(f"  [!] Skipped corrupt course record '{code}': {exc}")

    print(f"[✓] Loaded {len(students)} student(s) and {len(courses)} course(s) from:")
    print(f"    {DATA_PATH}")
    return students, courses
