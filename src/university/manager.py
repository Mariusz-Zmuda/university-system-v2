"""
manager.py — UniversityManager, central orchestration layer.

The only module that holds both student and course registries.
All cross-model operations pass through here.

Models (Student, Course) know nothing about each other.
Manager wires them together and enforces all business rules.
"""

import logging

from university import persistence
from university.exceptions import (
    AcademicDismissalError,
    CourseAlreadyCompletedError,
    CourseFullError,
    CourseNotFoundError,
    CreditLimitExceededError,
    DuplicateCourseError,
    DuplicateEnrollmentError,
    DuplicateStudentError,
    InvalidGradeError,
    PrerequisiteNotMetError,
    StudentNotFoundError,
)
from university.models.course import Course
from university.models.student import GRADE_POINTS, Student

logger = logging.getLogger(__name__)

# Dean's List thresholds
DEANS_LIST_GPA = 3.7
DEANS_LIST_MIN_CREDITS = 12


class UniversityManager:
    """
    Central orchestrator for the University Academic Management System.

    students : {student_id: Student}
    courses  : {course_code: Course}
    """

    def __init__(self) -> None:
        self.students: dict[str, Student] = {}
        self.courses: dict[str, Course] = {}

    # ------------------------------------------------------------------
    # Student management
    # ------------------------------------------------------------------

    def add_student(self, student: Student) -> None:
        """
        Register a new student.

        Raises:
            DuplicateStudentError: If a student with this ID already exists.
        """
        if student.id in self.students:
            raise DuplicateStudentError(student.id)
        self.students[student.id] = student
        logger.info("Added student %s (%s)", student.name, student.id)
        print(f"[✓] Student '{student.name}' ({student.id}) added.")

    def get_student(self, student_id: str) -> Student:
        """Raises StudentNotFoundError if ID does not exist."""
        if student_id not in self.students:
            raise StudentNotFoundError(student_id)
        return self.students[student_id]

    # ------------------------------------------------------------------
    # Course management
    # ------------------------------------------------------------------

    def add_course(self, course: Course) -> None:
        """
        Register a new course.

        Raises:
            DuplicateCourseError: If a course with this code already exists.
        """
        if course.course_code in self.courses:
            raise DuplicateCourseError(course.course_code)
        self.courses[course.course_code] = course
        logger.info("Added course %s (%s)", course.title, course.course_code)
        print(f"[✓] Course '{course.title}' ({course.course_code}) added.")

    def get_course(self, course_code: str) -> Course:
        """Raises CourseNotFoundError if code does not exist."""
        if course_code not in self.courses:
            raise CourseNotFoundError(course_code)
        return self.courses[course_code]

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------

    def enroll_student(self, student_id: str, course_code: str) -> None:
        """
        Enroll a student after validating all business rules in order:
        1. Student exists
        2. Course exists
        3. Student not dismissed
        4. Course not already completed
        5. Not already enrolled
        6. Prerequisites met
        7. Course not full
        8. Credit limit not exceeded
        """
        student = self.get_student(student_id)
        course = self.get_course(course_code)

        if student.academic_status == "Dismissed":
            raise AcademicDismissalError(student_id)

        if course_code in student.completed_courses:
            raise CourseAlreadyCompletedError(student_id, course_code)

        if course_code in student.enrolled_courses:
            raise DuplicateEnrollmentError(student_id, course_code)

        missing = [
            p for p in course.prerequisites if p not in student.completed_courses
        ]
        if missing:
            raise PrerequisiteNotMetError(course_code, missing)

        if course.is_full():
            raise CourseFullError(course_code)

        current = student.current_semester_credits(self.courses)
        if current + course.credits > Student.MAX_CREDITS:
            raise CreditLimitExceededError(current, course.credits, Student.MAX_CREDITS)

        student.enroll(course_code)
        course.add_student(student_id)
        logger.info("%s enrolled in %s", student_id, course_code)
        print(f"[✓] {student.name} enrolled in {course.title} ({course_code}).")

    def drop_course(self, student_id: str, course_code: str) -> None:
        """
        Remove a student from an in-progress course.

        Raises:
            StudentNotFoundError: Student ID unknown.
            CourseNotFoundError:  Student not enrolled in this course.
        """
        student = self.get_student(student_id)
        course = self.get_course(course_code)

        if course_code not in student.enrolled_courses:
            raise CourseNotFoundError(
                f"Student '{student_id}' is not enrolled in '{course_code}'."
            )

        student.drop(course_code)
        course.remove_student(student_id)
        logger.info("%s dropped %s", student_id, course_code)
        print(f"[✓] {student.name} dropped {course.title} ({course_code}).")

    # ------------------------------------------------------------------
    # Grade assignment
    # ------------------------------------------------------------------

    def assign_grade(self, student_id: str, course_code: str, grade: str) -> None:
        """
        Assign a final grade. Recalculates GPA and updates academic standing.

        Raises:
            StudentNotFoundError: Student ID unknown.
            CourseNotFoundError:  Course unknown or student not enrolled.
            InvalidGradeError:   Grade not in A, B, C, D, F.
        """
        student = self.get_student(student_id)
        self.get_course(course_code)

        grade = grade.upper()
        if grade not in GRADE_POINTS:
            raise InvalidGradeError(grade)

        if course_code not in student.enrolled_courses:
            raise CourseNotFoundError(
                f"Student '{student_id}' is not enrolled in '{course_code}'."
            )

        student.assign_grade(course_code, grade)
        gpa = student.calculate_gpa(self.courses)
        student.check_probation(gpa)

        logger.info(
            "Assigned %s to %s for %s — GPA: %.2f, Status: %s",
            grade,
            student_id,
            course_code,
            gpa,
            student.academic_status,
        )
        print(
            f"[✓] Assigned {grade} to {student.name} for {course_code}. "
            f"GPA: {gpa:.2f} | Status: {student.academic_status}"
        )

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def get_transcript(self, student_id: str) -> str:
        """Return formatted transcript for the given student."""
        return self.get_student(student_id).get_transcript(self.courses)

    def get_course_report(self, course_code: str) -> str:
        """Return formatted analytics report for the given course."""
        return self.get_course(course_code).get_course_report(self.students)

    def get_rankings(self) -> str:
        """
        Rank all students by GPA then total credits, highest first.
        Identifies Dean's List: GPA >= 3.7 AND credits >= 12.
        """
        ranked = sorted(
            self.students.values(),
            key=lambda s: (
                s.calculate_gpa(self.courses),
                s.total_credits_completed(self.courses),
            ),
            reverse=True,
        )

        lines: list[str] = [
            "=" * 52,
            "            STUDENT RANKINGS",
            "=" * 52,
            f"{'Rank':<6}{'Name':<22}{'GPA':<8}{'Credits':<10}{'Status'}",
            "-" * 52,
        ]

        deans_list: list[Student] = []

        for rank, student in enumerate(ranked, 1):
            gpa = student.calculate_gpa(self.courses)
            credits = student.total_credits_completed(self.courses)
            lines.append(
                f"{rank:<6}{student.name:<22}{gpa:<8.2f}"
                f"{credits:<10}{student.academic_status}"
            )
            qualifies = gpa >= DEANS_LIST_GPA
            qualifies = qualifies and credits >= DEANS_LIST_MIN_CREDITS
            if qualifies:
                deans_list.append(student)

        lines.append("=" * 52)

        if deans_list:
            lines += [
                "",
                f"🏆  DEAN'S LIST  "
                f"(GPA >= {DEANS_LIST_GPA}  and  >= {DEANS_LIST_MIN_CREDITS} credits)",
            ]
            for s in deans_list:
                lines.append(f"   ★ {s.name} — GPA {s.calculate_gpa(self.courses):.2f}")
        else:
            lines.append("No students currently qualify for the Dean's List.")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Save all data to JSON file."""
        persistence.save_data(self.students, self.courses)

    def load(self) -> None:
        """Load all data from JSON file."""
        self.students, self.courses = persistence.load_data()
