"""
test_student.py — Unit tests for the Student model.

Covers:
- GPA calculation (weighted average by UK credit hours)
- Academic status transitions (Good Standing / Probation / Dismissed)
- Credit calculations (semester and completed)
- Serialization round-trip (to_dict / from_dict)

UK credit values used throughout:
  COMP1001 = 15 credits
  MATH2003 = 30 credits
  ENGL1001 = 15 credits

Fixtures are defined in conftest.py and injected automatically by pytest.
"""

from __future__ import annotations

from university.models.course import Course
from university.models.student import Student


class TestGPA:
    """GPA calculation — weighted average by UK credit hours."""

    def test_no_courses_returns_zero(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        assert student.calculate_gpa(course_registry) == 0.0

    def test_single_a_grade(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        student.completed_courses = {"COMP1001": "A"}
        assert student.calculate_gpa(course_registry) == 4.0

    def test_single_f_grade(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        student.completed_courses = {"COMP1001": "F"}
        assert student.calculate_gpa(course_registry) == 0.0

    def test_weighted_average_two_courses(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        # COMP1001 (15cr, A=4.0) + MATH2003 (30cr, B=3.0)
        # = (15*4 + 30*3) / 45 = (60+90) / 45 = 150/45 = 3.33
        student.completed_courses = {"COMP1001": "A", "MATH2003": "B"}
        assert student.calculate_gpa(course_registry) == 3.33

    def test_all_f_grades(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        student.completed_courses = {"COMP1001": "F", "MATH2003": "F"}
        assert student.calculate_gpa(course_registry) == 0.0

    def test_equal_credits_averages_evenly(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        # COMP1001 (15cr, C=2.0) + ENGL1001 (15cr, A=4.0)
        # = (15*2 + 15*4) / 30 = 90/30 = 3.0
        student.completed_courses = {"COMP1001": "C", "ENGL1001": "A"}
        assert student.calculate_gpa(course_registry) == 3.0


class TestAcademicStatus:
    """Academic standing transitions."""

    def test_good_standing_above_threshold(self, student: Student) -> None:
        student.check_probation(3.5)
        assert student.academic_status == "Good Standing"

    def test_probation_below_2_0(self, student: Student) -> None:
        student.check_probation(1.9)
        assert student.academic_status == "Probation"

    def test_boundary_exactly_2_0_is_good_standing(self, student: Student) -> None:
        student.check_probation(2.0)
        assert student.academic_status == "Good Standing"

    def test_dismissed_after_two_consecutive_below_1_0(
        self, student: Student
    ) -> None:
        student.check_probation(0.8)
        student.check_probation(0.5)
        assert student.academic_status == "Dismissed"

    def test_not_dismissed_after_one_low_semester(self, student: Student) -> None:
        student.check_probation(0.8)
        assert student.academic_status == "Probation"

    def test_dismissed_is_terminal(self, student: Student) -> None:
        """A perfect GPA semester cannot reverse dismissal."""
        student.check_probation(0.8)
        student.check_probation(0.5)
        student.check_probation(4.0)
        assert student.academic_status == "Dismissed"

    def test_recovery_from_probation_to_good_standing(
        self, student: Student
    ) -> None:
        student.check_probation(1.5)
        assert student.academic_status == "Probation"
        student.check_probation(3.5)
        assert student.academic_status == "Good Standing"

    def test_non_consecutive_low_gpas_do_not_dismiss(
        self, student: Student
    ) -> None:
        """Low → recovery → low should not trigger dismissal."""
        student.check_probation(0.8)  # low
        student.check_probation(3.0)  # recovery
        student.check_probation(0.5)  # low again — not consecutive
        assert student.academic_status == "Probation"


class TestCredits:
    """UK credit hour calculations."""

    def test_semester_credits_in_progress(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        # COMP1001=15cr + ENGL1001=15cr = 30
        student.enrolled_courses = {"COMP1001": None, "ENGL1001": None}
        assert student.current_semester_credits(course_registry) == 30

    def test_completed_credits(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        # COMP1001=15cr + MATH2003=30cr = 45
        student.completed_courses = {"COMP1001": "A", "MATH2003": "B"}
        assert student.total_credits_completed(course_registry) == 45

    def test_no_enrolled_courses_returns_zero(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        assert student.current_semester_credits(course_registry) == 0

    def test_no_completed_courses_returns_zero(
        self, student: Student, course_registry: dict[str, Course]
    ) -> None:
        assert student.total_credits_completed(course_registry) == 0


class TestEnrollDrop:
    """Low-level enroll/drop on the model (no validation)."""

    def test_enroll_adds_course_with_none_grade(self, student: Student) -> None:
        student.enroll("COMP1001")
        assert "COMP1001" in student.enrolled_courses
        assert student.enrolled_courses["COMP1001"] is None

    def test_drop_removes_course(self, student: Student) -> None:
        student.enroll("COMP1001")
        student.drop("COMP1001")
        assert "COMP1001" not in student.enrolled_courses

    def test_drop_nonexistent_is_noop(self, student: Student) -> None:
        student.drop("GHOST99")  # should not raise

    def test_assign_grade_moves_to_completed(self, student: Student) -> None:
        student.enroll("COMP1001")
        student.assign_grade("COMP1001", "B")
        assert "COMP1001" not in student.enrolled_courses
        assert student.completed_courses["COMP1001"] == "B"


class TestSerialization:
    """to_dict / from_dict round-trip."""

    def test_round_trip_preserves_all_fields(self, student: Student) -> None:
        student.completed_courses = {"COMP1001": "A"}
        student.academic_status = "Good Standing"
        student.semester_gpa_history = [3.5, 4.0]

        restored = Student.from_dict(student.to_dict())

        assert restored.id == student.id
        assert restored.name == student.name
        assert restored.major == student.major
        assert restored.completed_courses == student.completed_courses
        assert restored.academic_status == student.academic_status
        assert restored.semester_gpa_history == student.semester_gpa_history

    def test_from_dict_defaults_for_missing_optional_fields(self) -> None:
        minimal = {"id": "1234567", "name": "Test Student", "major": "Arts"}
        s = Student.from_dict(minimal)
        assert s.enrolled_courses == {}
        assert s.completed_courses == {}
        assert s.academic_status == "Good Standing"
        assert s.semester_gpa_history == []
