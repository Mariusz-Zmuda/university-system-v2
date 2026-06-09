"""
test_course.py — Unit tests for the Course model.

Covers:
- Capacity management (add, remove, is_full)
- Analytics: course_average, pass_rate, top_students
- Course report generation
- Serialization round-trip

UK course codes and credit values used throughout.
Fixtures are injected from conftest.py.
"""

from __future__ import annotations

from university.models.course import Course
from university.models.student import Student


class TestCapacity:
    """Enrollment capacity management."""

    def test_add_student(self, course_comp1001: Course) -> None:
        course_comp1001.add_student("1234567")
        assert "1234567" in course_comp1001.enrolled_students

    def test_add_student_no_duplicate(self, course_comp1001: Course) -> None:
        course_comp1001.add_student("1234567")
        course_comp1001.add_student("1234567")
        assert course_comp1001.enrolled_students.count("1234567") == 1

    def test_remove_student(self, course_comp1001: Course) -> None:
        course_comp1001.add_student("1234567")
        course_comp1001.remove_student("1234567")
        assert "1234567" not in course_comp1001.enrolled_students

    def test_remove_nonexistent_is_noop(self, course_comp1001: Course) -> None:
        course_comp1001.remove_student("9999999")  # should not raise

    def test_is_full_false_when_space_available(self, course_comp1001: Course) -> None:
        assert not course_comp1001.is_full()

    def test_is_full_true_at_capacity(self, course_tiny: Course) -> None:
        course_tiny.add_student("1234567")
        assert course_tiny.is_full()

    def test_is_full_false_when_empty(self, course_tiny: Course) -> None:
        assert not course_tiny.is_full()


class TestCourseAverage:
    """course_average() — mean GPA points for graded students."""

    def test_average_no_graded_students(
        self,
        course_comp1001: Course,
        student: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        assert course_comp1001.course_average({"1234567": student}) == 0.0

    def test_average_single_a(
        self,
        course_comp1001: Course,
        student: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        student.completed_courses = {"COMP1001": "A"}
        assert course_comp1001.course_average({"1234567": student}) == 4.0

    def test_average_two_students(
        self,
        course_comp1001: Course,
        student: Student,
        student_b: Student,
    ) -> None:
        # Alice: A (4.0), Bob: B (3.0) → average = 3.5
        course_comp1001.add_student(student.id)
        course_comp1001.add_student(student_b.id)
        student.completed_courses = {"COMP1001": "A"}
        student_b.completed_courses = {"COMP1001": "B"}
        registry = {"1234567": student, "7654321": student_b}
        assert course_comp1001.course_average(registry) == 3.5

    def test_average_all_f(
        self,
        course_comp1001: Course,
        student: Student,
        student_b: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        course_comp1001.add_student(student_b.id)
        student.completed_courses = {"COMP1001": "F"}
        student_b.completed_courses = {"COMP1001": "F"}
        registry = {"1234567": student, "7654321": student_b}
        assert course_comp1001.course_average(registry) == 0.0


class TestPassRate:
    """pass_rate() — percentage of graded students who did not fail."""

    def test_pass_rate_no_grades(
        self,
        course_comp1001: Course,
        student: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        assert course_comp1001.pass_rate({"1234567": student}) == 0.0

    def test_pass_rate_100_percent(
        self,
        course_comp1001: Course,
        student: Student,
        student_b: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        course_comp1001.add_student(student_b.id)
        student.completed_courses = {"COMP1001": "A"}
        student_b.completed_courses = {"COMP1001": "C"}
        registry = {"1234567": student, "7654321": student_b}
        assert course_comp1001.pass_rate(registry) == 100.0

    def test_pass_rate_50_percent(
        self,
        course_comp1001: Course,
        student: Student,
        student_b: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        course_comp1001.add_student(student_b.id)
        student.completed_courses = {"COMP1001": "A"}
        student_b.completed_courses = {"COMP1001": "F"}
        registry = {"1234567": student, "7654321": student_b}
        assert course_comp1001.pass_rate(registry) == 50.0

    def test_pass_rate_0_percent(
        self,
        course_comp1001: Course,
        student: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        student.completed_courses = {"COMP1001": "F"}
        assert course_comp1001.pass_rate({"1234567": student}) == 0.0


class TestTopStudents:
    """top_students() — ranked by grade descending."""

    def test_top_students_empty_when_none_graded(
        self,
        course_comp1001: Course,
        student: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        result = course_comp1001.top_students({"1234567": student})
        assert result == []

    def test_top_students_ordering(
        self,
        course_comp1001: Course,
        student: Student,
        student_b: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        course_comp1001.add_student(student_b.id)
        student.completed_courses = {"COMP1001": "B"}
        student_b.completed_courses = {"COMP1001": "A"}
        registry = {"1234567": student, "7654321": student_b}
        top = course_comp1001.top_students(registry)
        # Bob (A) should rank above Alice (B)
        assert top[0][2] == "A"
        assert top[1][2] == "B"

    def test_top_students_respects_n(
        self,
        course_comp1001: Course,
        student: Student,
        student_b: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        course_comp1001.add_student(student_b.id)
        student.completed_courses = {"COMP1001": "A"}
        student_b.completed_courses = {"COMP1001": "B"}
        registry = {"1234567": student, "7654321": student_b}
        top = course_comp1001.top_students(registry, n=1)
        assert len(top) == 1

    def test_top_students_returns_correct_tuple_structure(
        self,
        course_comp1001: Course,
        student: Student,
    ) -> None:
        course_comp1001.add_student(student.id)
        student.completed_courses = {"COMP1001": "A"}
        top = course_comp1001.top_students({"1234567": student})
        assert len(top) == 1
        sid, name, grade = top[0]
        assert sid == "1234567"
        assert name == "Alice Johnson"
        assert grade == "A"


class TestSerialization:
    """to_dict / from_dict round-trip."""

    def test_round_trip_preserves_all_fields(self, course_comp2001: Course) -> None:
        course_comp2001.add_student("1234567")
        restored = Course.from_dict(course_comp2001.to_dict())
        assert restored.course_code == course_comp2001.course_code
        assert restored.title == course_comp2001.title
        assert restored.credits == course_comp2001.credits
        assert restored.max_capacity == course_comp2001.max_capacity
        assert restored.prerequisites == course_comp2001.prerequisites
        assert restored.enrolled_students == course_comp2001.enrolled_students

    def test_from_dict_defaults_for_missing_optional_fields(self) -> None:
        minimal = {
            "course_code": "PHYS1001",
            "title": "Physics I",
            "credits": 15,
            "max_capacity": 20,
        }
        c = Course.from_dict(minimal)
        assert c.prerequisites == []
        assert c.enrolled_students == []
