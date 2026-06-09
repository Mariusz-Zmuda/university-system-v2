"""
conftest.py — Shared pytest fixtures.

Test data uses US-style credit conventions (matching the assignment spec):
  Student IDs  : 7 digits           e.g. 1234567
  Course codes : alphanumeric       e.g. COMP1001
  Credits      : 3 or 4 per course
  Semester cap : 18 credits

Fixtures defined here are automatically available to all test modules
without any import.
"""

from __future__ import annotations

import pytest

from university.manager import UniversityManager
from university.models.course import Course
from university.models.student import Student


# ---------------------------------------------------------------------------
# Raw model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def student() -> Student:
    """A blank student with no courses."""
    return Student(id="1234567", name="Alice Johnson", major="Computer Science")


@pytest.fixture
def student_b() -> Student:
    """A second blank student for multi-student tests."""
    return Student(id="7654321", name="Bob Smith", major="Mathematics")


@pytest.fixture
def course_comp1001() -> Course:
    """Introductory CS module — 3 credits, no prerequisites, capacity 30."""
    return Course("COMP1001", "Intro to Computer Science", 3, 30)


@pytest.fixture
def course_comp2001() -> Course:
    """Intermediate CS module — 3 credits, requires COMP1001."""
    return Course("COMP2001", "Data Structures", 3, 30, prerequisites=["COMP1001"])


@pytest.fixture
def course_math2003() -> Course:
    """Calculus module — 4 credits, no prerequisites."""
    return Course("MATH2003", "Calculus I", 4, 25)


@pytest.fixture
def course_engl1001() -> Course:
    """English module — 3 credits, no prerequisites."""
    return Course("ENGL1001", "English Composition", 3, 20)


@pytest.fixture
def course_tiny() -> Course:
    """Capacity-1 module used to test CourseFullError."""
    return Course("TINY01", "Tiny Course", 3, 1)


@pytest.fixture
def course_registry(
    course_comp1001: Course,
    course_comp2001: Course,
    course_math2003: Course,
    course_engl1001: Course,
) -> dict[str, Course]:
    """Dict of courses for passing directly into Student methods."""
    return {
        "COMP1001": course_comp1001,
        "COMP2001": course_comp2001,
        "MATH2003": course_math2003,
        "ENGL1001": course_engl1001,
    }


# ---------------------------------------------------------------------------
# Manager fixture — fully wired system
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr(
    student: Student,
    student_b: Student,
    course_comp1001: Course,
    course_comp2001: Course,
    course_math2003: Course,
    course_engl1001: Course,
    course_tiny: Course,
) -> UniversityManager:
    """
    A UniversityManager pre-loaded with two students and five courses.

    Students : 1234567 Alice Johnson (CS), 7654321 Bob Smith (Math)
    Courses  : COMP1001, COMP2001 (prereq COMP1001), MATH2003,
               ENGL1001, TINY01 (capacity 1)
    """
    m = UniversityManager()
    m.add_student(student)
    m.add_student(student_b)
    m.add_course(course_comp1001)
    m.add_course(course_comp2001)
    m.add_course(course_math2003)
    m.add_course(course_engl1001)
    m.add_course(course_tiny)
    return m


# ---------------------------------------------------------------------------
# Convenience: manager with graded students for course analytics tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr_with_grades(mgr: UniversityManager) -> UniversityManager:
    """
    Manager where both students have completed COMP1001 with known grades.

    Alice → A (4.0), Bob → B (3.0). Useful for analytics and ranking tests.
    """
    mgr.enroll_student("1234567", "COMP1001")
    mgr.assign_grade("1234567", "COMP1001", "A")
    mgr.enroll_student("7654321", "COMP1001")
    mgr.assign_grade("7654321", "COMP1001", "B")
    return mgr
