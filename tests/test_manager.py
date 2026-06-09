"""
test_manager.py — Integration tests for UniversityManager.

Tests cross-model operations: enrollment validation, grade assignment,
academic standing updates, and report generation.

UK academic conventions throughout:
  Student IDs : 7 digits       e.g. 1234567
  Course codes: alphanumeric   e.g. COMP1001
  Credits     : 15 or 30
  Annual limit: 120 credits

All fixtures come from conftest.py.
"""

from __future__ import annotations

import pytest

from university.exceptions import (
    AcademicDismissalError,
    CourseAlreadyCompletedError,
    CourseFullError,
    CreditLimitExceededError,
    DuplicateCourseError,
    DuplicateEnrollmentError,
    DuplicateStudentError,
    InvalidGradeError,
    PrerequisiteNotMetError,
    StudentNotFoundError,
)
from university.manager import UniversityManager
from university.models.course import Course
from university.models.student import Student


class TestRegistration:
    """Adding students and courses — duplicate detection."""

    def test_duplicate_student_raises(self, mgr: UniversityManager) -> None:
        with pytest.raises(DuplicateStudentError):
            mgr.add_student(Student("1234567", "Clone", "CS"))

    def test_duplicate_course_raises(self, mgr: UniversityManager) -> None:
        with pytest.raises(DuplicateCourseError):
            mgr.add_course(Course("COMP1001", "Duplicate", 15, 10))

    def test_get_student_not_found_raises(self, mgr: UniversityManager) -> None:
        with pytest.raises(StudentNotFoundError):
            mgr.get_student("0000000")


class TestEnrollmentHappyPath:
    """Enrollment succeeds when all rules are satisfied."""

    def test_basic_enrollment(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        assert "COMP1001" in mgr.students["1234567"].enrolled_courses

    def test_course_enrolled_students_updated(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        assert "1234567" in mgr.courses["COMP1001"].enrolled_students

    def test_enroll_after_prerequisite_completed(
        self, mgr: UniversityManager
    ) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "B")
        mgr.enroll_student("1234567", "COMP2001")  # prereq now met
        assert "COMP2001" in mgr.students["1234567"].enrolled_courses


class TestEnrollmentGuards:
    """Each business rule raises the correct exception."""

    def test_unknown_student_raises(self, mgr: UniversityManager) -> None:
        with pytest.raises(StudentNotFoundError):
            mgr.enroll_student("0000000", "COMP1001")

    def test_prerequisite_not_met(self, mgr: UniversityManager) -> None:
        with pytest.raises(PrerequisiteNotMetError):
            mgr.enroll_student("1234567", "COMP2001")

    def test_duplicate_enrollment(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        with pytest.raises(DuplicateEnrollmentError):
            mgr.enroll_student("1234567", "COMP1001")

    def test_already_completed(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "A")
        with pytest.raises(CourseAlreadyCompletedError):
            mgr.enroll_student("1234567", "COMP1001")

    def test_course_full(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "TINY01")
        with pytest.raises(CourseFullError):
            mgr.enroll_student("7654321", "TINY01")

    def test_credit_limit_exceeded(self, mgr: UniversityManager) -> None:
        # UK annual limit = 120 credits
        # Enroll in 4 x 30-credit modules = 120 credits (at the limit)
        for i in range(4):
            code = f"FULL{i}001"
            mgr.add_course(Course(code, f"Full Year Module {i}", 30, 10))
            mgr.enroll_student("1234567", code)
        # Now at 120 credits — any additional module should raise
        mgr.add_course(Course("OVER1001", "Over Limit", 15, 10))
        with pytest.raises(CreditLimitExceededError):
            mgr.enroll_student("1234567", "OVER1001")

    def test_dismissed_student_cannot_enroll(self, mgr: UniversityManager) -> None:
        mgr.students["1234567"].academic_status = "Dismissed"
        with pytest.raises(AcademicDismissalError):
            mgr.enroll_student("1234567", "COMP1001")


class TestDropCourse:
    """Dropping an enrolled course."""

    def test_drop_removes_from_student(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.drop_course("1234567", "COMP1001")
        assert "COMP1001" not in mgr.students["1234567"].enrolled_courses

    def test_drop_removes_from_course(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.drop_course("1234567", "COMP1001")
        assert "1234567" not in mgr.courses["COMP1001"].enrolled_students


class TestGradeAssignment:
    """Grading moves courses and updates GPA and standing."""

    def test_grade_moves_to_completed(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "A")
        assert "COMP1001" in mgr.students["1234567"].completed_courses
        assert "COMP1001" not in mgr.students["1234567"].enrolled_courses

    def test_gpa_updates_after_grade(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "A")
        assert mgr.students["1234567"].calculate_gpa(mgr.courses) == 4.0

    def test_probation_after_f_grade(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "F")
        assert mgr.students["1234567"].academic_status == "Probation"

    def test_good_standing_after_passing_grade(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "B")
        assert mgr.students["1234567"].academic_status == "Good Standing"

    def test_invalid_grade_raises(self, mgr: UniversityManager) -> None:
        mgr.enroll_student("1234567", "COMP1001")
        with pytest.raises(InvalidGradeError):
            mgr.assign_grade("1234567", "COMP1001", "Z")


class TestReports:
    """Transcript, course report, and rankings smoke tests."""

    def test_transcript_contains_student_name(
        self, mgr_with_grades: UniversityManager
    ) -> None:
        transcript = mgr_with_grades.get_transcript("1234567")
        assert "Alice Johnson" in transcript

    def test_transcript_contains_grade(
        self, mgr_with_grades: UniversityManager
    ) -> None:
        transcript = mgr_with_grades.get_transcript("1234567")
        assert "A" in transcript

    def test_course_report_contains_course_code(
        self, mgr_with_grades: UniversityManager
    ) -> None:
        report = mgr_with_grades.get_course_report("COMP1001")
        assert "COMP1001" in report

    def test_course_report_contains_pass_rate(
        self, mgr_with_grades: UniversityManager
    ) -> None:
        report = mgr_with_grades.get_course_report("COMP1001")
        assert "Pass Rate" in report

    def test_rankings_contains_all_students(
        self, mgr_with_grades: UniversityManager
    ) -> None:
        rankings = mgr_with_grades.get_rankings()
        assert "Alice Johnson" in rankings
        assert "Bob Smith" in rankings

    def test_rankings_higher_gpa_ranks_first(
        self, mgr_with_grades: UniversityManager
    ) -> None:
        # Alice has A (4.0), Bob has B (3.0) — Alice should appear first
        rankings = mgr_with_grades.get_rankings()
        alice_pos = rankings.index("Alice Johnson")
        bob_pos = rankings.index("Bob Smith")
        assert alice_pos < bob_pos

    def test_deans_list_appears_when_qualified(
        self, mgr: UniversityManager
    ) -> None:
        # Dean's List: GPA >= 3.7 AND >= 12 credits
        # One 15-credit module with A is enough (15cr >= 12, GPA 4.0 >= 3.7)
        mgr.enroll_student("1234567", "COMP1001")
        mgr.assign_grade("1234567", "COMP1001", "A")
        rankings = mgr.get_rankings()
        assert "DEAN'S LIST" in rankings


class TestPersistenceRoundTrip:
    """Save → load preserves all state."""

    def test_round_trip(
        self, mgr_with_grades: UniversityManager, tmp_path: pytest.TempPathFactory
    ) -> None:
        import json
        from pathlib import Path
        from unittest.mock import patch

        import university.persistence as persistence_module

        path = Path(str(tmp_path)) / "test_data.json"

        with patch.object(persistence_module, "DATA_PATH", path):
            persistence_module.save_data(
                mgr_with_grades.students,
                mgr_with_grades.courses,
            )

        assert path.exists()
        data = json.loads(path.read_text())
        assert "1234567" in data["students"]
        assert "COMP1001" in data["courses"]
        assert data["students"]["1234567"]["completed_courses"]["COMP1001"] == "A"
