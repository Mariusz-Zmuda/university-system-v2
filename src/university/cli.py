"""
cli.py — Interactive menu for the University Academic Management System.

All user I/O lives here. Zero business logic.

Input validation rules (UK academic system):
  Student ID  : exactly 7 digits            e.g. 1234567
  Course code : alphanumeric, auto-uppercased e.g. COMP1001
  Credits     : 15 or 30 only
  Name        : letters and spaces, title-cased on save
  Grade       : A, B, C, D, or F

Key UX behaviours:
  - Format hint shown BEFORE the user types
  - On invalid input: explain why + retry (not kick back to menu)
  - Empty Enter at any validated prompt = cancel → back to menu
  - Never crashes
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

from university.exceptions import UniversityError
from university.manager import UniversityManager
from university.models.course import Course
from university.models.student import Student

logger = logging.getLogger(__name__)

# Sentinel returned when user presses Enter with nothing — means "cancel"
_CANCELLED = "__CANCELLED__"

# Valid UK module credit values
_VALID_CREDITS = {15, 30}


# ---------------------------------------------------------------------------
# Low-level prompt helpers
# ---------------------------------------------------------------------------

def _prompt(msg: str) -> str:
    """Raw prompt — strips whitespace, no validation."""
    return input(msg).strip()


def _prompt_or_cancel(msg: str) -> str:
    """
    Prompt the user. If they press Enter with nothing, return _CANCELLED.
    Callers check for _CANCELLED and return early to the menu.
    """
    value = input(msg).strip()
    if not value:
        print("  [↩] Cancelled — returning to menu.")
        return _CANCELLED
    return value


# ---------------------------------------------------------------------------
# Validated field prompts
# Each shows format upfront, retries on bad input, cancels on empty Enter.
# ---------------------------------------------------------------------------

def _ask_student_id() -> str:
    """
    Prompt for a UK student ID.
    Format: exactly 7 digits, e.g. 1234567
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print("  Student ID  — 7 digits only  (e.g. 1234567)")
    while True:
        raw = _prompt_or_cancel("  Enter ID    : ")
        if raw == _CANCELLED:
            return _CANCELLED
        if re.fullmatch(r"\d{7}", raw):
            return raw
        print(f"  [!] '{raw}' is not valid. Must be exactly 7 digits — no letters, spaces or symbols.")
        print("      Example: 1234567")


def _ask_course_code() -> str:
    """
    Prompt for a UK module code.
    Format: alphanumeric only, auto-uppercased, 4-8 characters.
    e.g. COMP1001, MATH2003, PHYS3010
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print("  Course code — letters and digits only, auto-uppercased  (e.g. COMP1001)")
    while True:
        raw = _prompt_or_cancel("  Enter code  : ")
        if raw == _CANCELLED:
            return _CANCELLED
        normalised = raw.upper()
        if re.fullmatch(r"[A-Z0-9]{2,8}", normalised):
            return normalised
        print(f"  [!] '{raw}' is not valid. Use 2–8 letters/digits only, no spaces or symbols.")
        print("      Examples: COMP1001  MATH2003  PHYS301")


def _ask_name(label: str = "Full name") -> str:
    """
    Prompt for a person's name.
    Accepts letters and spaces only. Stored in Title Case.
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print(f"  {label}   — letters and spaces only  (e.g. Alice Johnson)")
    while True:
        raw = _prompt_or_cancel(f"  Enter name  : ")
        if raw == _CANCELLED:
            return _CANCELLED
        if re.fullmatch(r"[A-Za-z\s\-']+", raw) and raw.strip():
            return raw.strip().title()
        print(f"  [!] '{raw}' contains invalid characters. Letters, spaces, hyphens and apostrophes only.")
        print("      Examples: Alice Johnson  O'Brien  Smith-Jones")


def _ask_major() -> str:
    """
    Prompt for a major/programme name.
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print("  Major/Programme  (e.g. Computer Science)")
    while True:
        raw = _prompt_or_cancel("  Enter major : ")
        if raw == _CANCELLED:
            return _CANCELLED
        if len(raw) >= 2:
            return raw.strip().title()
        print("  [!] Major must be at least 2 characters.")


def _ask_credits() -> int | str:
    """
    Prompt for UK module credits.
    Only 15 or 30 are accepted.
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print("  Credits — UK standard: 15 (one semester) or 30 (full year)")
    while True:
        raw = _prompt_or_cancel("  Enter credits: ")
        if raw == _CANCELLED:
            return _CANCELLED
        if raw.isdigit() and int(raw) in _VALID_CREDITS:
            return int(raw)
        print(f"  [!] '{raw}' is not valid. Only 15 or 30 are accepted in the UK credit system.")
        print("      15 = one semester module  |  30 = full year module")


def _ask_capacity() -> int | str:
    """
    Prompt for max student capacity. Any positive integer.
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print("  Max capacity — maximum number of students  (e.g. 30)")
    while True:
        raw = _prompt_or_cancel("  Enter capacity: ")
        if raw == _CANCELLED:
            return _CANCELLED
        if raw.isdigit() and int(raw) >= 1:
            return int(raw)
        print(f"  [!] '{raw}' is not valid. Must be a whole number of at least 1.")


def _ask_grade() -> str:
    """
    Prompt for a letter grade. Accepts A, B, C, D, F only.
    Returns _CANCELLED if user presses Enter with nothing.
    """
    print("  Grade — A (4.0)  B (3.0)  C (2.0)  D (1.0)  F (0.0)")
    while True:
        raw = _prompt_or_cancel("  Enter grade : ")
        if raw == _CANCELLED:
            return _CANCELLED
        normalised = raw.upper()
        if normalised in {"A", "B", "C", "D", "F"}:
            return normalised
        print(f"  [!] '{raw}' is not a valid grade. Choose from: A  B  C  D  F")


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

_MENU = """
╔══════════════════════════════════════════════╗
║    University Academic Management System     ║
╠══════════════════════════════════════════════╣
║  1.  Add Student                             ║
║  2.  Add Course                              ║
║  3.  Enroll Student in Course                ║
║  4.  Assign Grade                            ║
║  5.  Drop Course                             ║
║  6.  View Transcript                         ║
║  7.  View Course Report                      ║
║  8.  View Rankings                           ║
║  9.  Save Data                               ║
║  10. Load Data                               ║
║  11. Exit                                    ║
╚══════════════════════════════════════════════╝"""


# ---------------------------------------------------------------------------
# Handlers — one per menu item
# ---------------------------------------------------------------------------

def _add_student(mgr: UniversityManager) -> None:
    print("\n── Add Student ──────────────────────────────")
    sid = _ask_student_id()
    if sid == _CANCELLED:
        return

    name = _ask_name("Full name")
    if name == _CANCELLED:
        return

    major = _ask_major()
    if major == _CANCELLED:
        return

    mgr.add_student(Student(id=sid, name=name, major=major))


def _add_course(mgr: UniversityManager) -> None:
    print("\n── Add Course ───────────────────────────────")
    code = _ask_course_code()
    if code == _CANCELLED:
        return

    print("  Course title  (e.g. Introduction to Computer Science)")
    title = _prompt_or_cancel("  Enter title : ")
    if title == _CANCELLED:
        return
    title = title.strip().title()

    credits = _ask_credits()
    if credits == _CANCELLED:
        return

    capacity = _ask_capacity()
    if capacity == _CANCELLED:
        return

    print("  Prerequisites — comma-separated course codes, or press Enter for none")
    raw = _prompt("  Enter prereqs: ")
    prereqs = [p.strip().upper() for p in raw.split(",") if p.strip()]

    mgr.add_course(
        Course(
            course_code=code,
            title=title,
            credits=int(credits),
            max_capacity=int(capacity),
            prerequisites=prereqs,
        )
    )


def _enroll(mgr: UniversityManager) -> None:
    print("\n── Enroll Student ───────────────────────────")
    print("  Student ID  — 7 digits  (e.g. 1234567)")
    sid = _prompt_or_cancel("  Enter ID    : ")
    if sid == _CANCELLED:
        return
    if not re.fullmatch(r"\d{7}", sid):
        print(f"  [!] '{sid}' is not a valid student ID.")
        return

    print("  Course code — alphanumeric  (e.g. COMP1001)")
    code = _prompt_or_cancel("  Enter code  : ")
    if code == _CANCELLED:
        return
    mgr.enroll_student(sid, code.upper())


def _assign_grade(mgr: UniversityManager) -> None:
    print("\n── Assign Grade ─────────────────────────────")
    print("  Student ID  — 7 digits  (e.g. 1234567)")
    sid = _prompt_or_cancel("  Enter ID    : ")
    if sid == _CANCELLED:
        return

    print("  Course code — alphanumeric  (e.g. COMP1001)")
    code = _prompt_or_cancel("  Enter code  : ")
    if code == _CANCELLED:
        return

    grade = _ask_grade()
    if grade == _CANCELLED:
        return

    mgr.assign_grade(sid, code.upper(), grade)


def _drop(mgr: UniversityManager) -> None:
    print("\n── Drop Course ──────────────────────────────")
    print("  Student ID  — 7 digits  (e.g. 1234567)")
    sid = _prompt_or_cancel("  Enter ID    : ")
    if sid == _CANCELLED:
        return

    print("  Course code — alphanumeric  (e.g. COMP1001)")
    code = _prompt_or_cancel("  Enter code  : ")
    if code == _CANCELLED:
        return

    mgr.drop_course(sid, code.upper())


def _transcript(mgr: UniversityManager) -> None:
    print("\n── View Transcript ──────────────────────────")
    print("  Student ID  — 7 digits  (e.g. 1234567)")
    sid = _prompt_or_cancel("  Enter ID    : ")
    if sid == _CANCELLED:
        return
    print(mgr.get_transcript(sid))


def _course_report(mgr: UniversityManager) -> None:
    print("\n── Course Report ────────────────────────────")
    print("  Course code — alphanumeric  (e.g. COMP1001)")
    code = _prompt_or_cancel("  Enter code  : ")
    if code == _CANCELLED:
        return
    print(mgr.get_course_report(code.upper()))


def _rankings(mgr: UniversityManager) -> None:
    print(mgr.get_rankings())


_HANDLERS: dict[str, Callable[[UniversityManager], None]] = {
    "1": _add_student,
    "2": _add_course,
    "3": _enroll,
    "4": _assign_grade,
    "5": _drop,
    "6": _transcript,
    "7": _course_report,
    "8": _rankings,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """Start the interactive CLI. Called from main.py and the installed script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        handlers=[logging.FileHandler("university.log"), logging.NullHandler()],
    )

    mgr = UniversityManager()
    mgr.load()

    while True:
        print(_MENU)
        choice = _prompt("Select option: ")

        if choice == "11":
            if _prompt("Save before exiting? (y/n): ").lower() == "y":
                mgr.save()
            print("Goodbye.")
            break

        if choice == "9":
            mgr.save()
            continue

        if choice == "10":
            # Warn if unsaved work exists in memory
            if mgr.students or mgr.courses:
                confirm = _prompt(
                    f"  [!] This will overwrite {len(mgr.students)} student(s) "
                    f"and {len(mgr.courses)} course(s) in memory.\n"
                    "      Any unsaved changes will be lost. Continue? (y/n): "
                )
                if confirm.lower() != "y":
                    print("  [↩] Load cancelled.")
                    continue
            mgr.load()
            continue

        handler = _HANDLERS.get(choice)
        if handler is None:
            print("  [!] Invalid option. Choose 1–11.")
            continue

        try:
            handler(mgr)
        except UniversityError as exc:
            print(f"\n  [✗] {exc}\n")
            logger.warning("Business rule violation: %s", exc)
        except KeyboardInterrupt:
            print("\n  [!] Cancelled.")
        except Exception as exc:  # noqa: BLE001
            print(f"\n  [!] Unexpected error: {exc}\n")
            logger.exception("Unhandled exception in menu loop")
