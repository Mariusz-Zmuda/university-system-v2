"""
student.py — Student model.

Responsibilities:
- Track enrollment state (in-progress and completed courses)
- Calculate GPA (weighted by credits, 4.0 scale) — both semester and cumulative
- Track and update academic standing (Good Standing / Probation / Dismissed)
- Generate official transcripts
"""

from university.exceptions import InvalidGradeError
from university.models.person import Person

# Grade to GPA points mapping (4.0 scale)
GRADE_POINTS: dict[str, float] = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0,
}


class Student(Person):
    """
    Represents a university student.

    enrolled_courses  : {course_code: grade | None} — None means in progress
    completed_courses : {course_code: grade}         — finalised with grade
    semester_courses  : set of course codes graded in the CURRENT semester,
                        used to compute semester GPA separately from cumulative
    """

    # Spec: maximum 18 credits per semester
    MAX_CREDITS: int = 18

    def __init__(
        self,
        id: str,
        name: str,
        major: str,
        enrolled_courses: dict[str, str | None] | None = None,
        completed_courses: dict[str, str] | None = None,
        academic_status: str = "Good Standing",
        semester_gpa_history: list[float] | None = None,
        semester_courses: list[str] | None = None,
    ) -> None:
        super().__init__(id, name)
        self.major = major
        self.enrolled_courses: dict[str, str | None] = enrolled_courses or {}
        self.completed_courses: dict[str, str] = completed_courses or {}
        self.academic_status = academic_status
        self.semester_gpa_history: list[float] = semester_gpa_history or []
        # Courses graded in the current (in-progress) semester
        self.semester_courses: list[str] = semester_courses or []

    # ------------------------------------------------------------------
    # Enrollment helpers
    # ------------------------------------------------------------------

    def enroll(self, course_code: str) -> None:
        """Add a course with no grade yet."""
        self.enrolled_courses[course_code] = None

    def drop(self, course_code: str) -> None:
        """Remove a course. No-op if not enrolled."""
        self.enrolled_courses.pop(course_code, None)

    def assign_grade(self, course_code: str, grade: str) -> None:
        """
        Finalise a grade — moves course from enrolled to completed and
        records it as part of the current semester.

        Raises:
            InvalidGradeError: If grade is not A, B, C, D or F.
        """
        grade = grade.upper()
        if grade not in GRADE_POINTS:
            raise InvalidGradeError(grade)
        self.enrolled_courses.pop(course_code, None)
        self.completed_courses[course_code] = grade
        if course_code not in self.semester_courses:
            self.semester_courses.append(course_code)

    # ------------------------------------------------------------------
    # GPA & credits
    # ------------------------------------------------------------------

    def _weighted_gpa(self, codes: list[str], course_registry: dict) -> float:
        """Weighted GPA over the given course codes. Helper for the two GPAs."""
        total_points = 0.0
        total_credits = 0
        for code in codes:
            grade = self.completed_courses.get(code)
            if grade is None:
                continue
            course = course_registry.get(code)
            credits = course.credits if course else 3
            total_points += GRADE_POINTS[grade] * credits
            total_credits += credits
        if total_credits == 0:
            return 0.0
        return round(total_points / total_credits, 2)

    def calculate_gpa(self, course_registry: dict) -> float:
        """Cumulative GPA — weighted across ALL completed courses."""
        return self._weighted_gpa(list(self.completed_courses.keys()), course_registry)

    def calculate_semester_gpa(self, course_registry: dict) -> float:
        """Semester GPA — weighted across only the CURRENT semester's courses."""
        return self._weighted_gpa(self.semester_courses, course_registry)

    def current_semester_credits(self, course_registry: dict) -> int:
        """Sum of credits for currently enrolled (in-progress) courses."""
        return sum(
            course_registry[code].credits
            for code in self.enrolled_courses
            if code in course_registry
        )

    def total_credits_completed(self, course_registry: dict) -> int:
        """Sum of credits for all completed courses."""
        return sum(
            course_registry[code].credits
            for code in self.completed_courses
            if code in course_registry
        )

    # ------------------------------------------------------------------
    # Academic standing
    # ------------------------------------------------------------------

    def check_probation(self, gpa: float) -> None:
        """
        Update academic status after a grade is assigned.

        Rules:
        - GPA < 2.0 for one semester  → Probation
        - GPA < 1.0 for two consecutive semesters → Dismissed
        - Dismissed is permanent — cannot be reversed
        """
        if self.academic_status == "Dismissed":
            return

        self.semester_gpa_history.append(gpa)

        consecutive_low = (
            len(self.semester_gpa_history) >= 2
            and self.semester_gpa_history[-1] < 1.0
            and self.semester_gpa_history[-2] < 1.0
        )

        if consecutive_low:
            self.academic_status = "Dismissed"
        elif gpa < 2.0:
            self.academic_status = "Probation"
        else:
            self.academic_status = "Good Standing"

    # ------------------------------------------------------------------
    # Transcript
    # ------------------------------------------------------------------

    def get_transcript(self, course_registry: dict) -> str:
        """Generate a formatted official transcript string."""
        lines: list[str] = [
            "=" * 44,
            "         OFFICIAL TRANSCRIPT",
            "=" * 44,
            f"Name   : {self.name}",
            f"ID     : {self.id}",
            f"Major  : {self.major}",
            f"Status : {self.academic_status}",
            "-" * 44,
            f"{'Course':<12} {'Title':<18} {'Gr':>3} {'Cr':>3}",
            "-" * 44,
        ]

        for code, grade in self.completed_courses.items():
            course = course_registry.get(code)
            credits = course.credits if course else 3
            title = (course.title if course else code)[:17]
            lines.append(f"{code:<12} {title:<18} {grade:>3} {credits:>3}")

        lines.append("-" * 44)
        sem_gpa = self.calculate_semester_gpa(course_registry)
        cum_gpa = self.calculate_gpa(course_registry)
        total_cr = self.total_credits_completed(course_registry)

        lines += [
            f"Semester GPA   : {sem_gpa:.2f}",
            f"Cumulative GPA : {cum_gpa:.2f}",
            f"Total Credits  : {total_cr}",
        ]

        if self.enrolled_courses:
            lines += ["", "In Progress:"]
            for code in self.enrolled_courses:
                course = course_registry.get(code)
                title = (course.title if course else code)[:17]
                credits = course.credits if course else 3
                lines.append(f"  {code:<12} {title:<18} {'—':>3} {credits:>3}")

        lines.append("=" * 44)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def get_details(self) -> str:
        return (
            f"Student | ID: {self.id} | Name: {self.name} | "
            f"Major: {self.major} | Status: {self.academic_status}"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "major": self.major,
            "enrolled_courses": self.enrolled_courses,
            "completed_courses": self.completed_courses,
            "academic_status": self.academic_status,
            "semester_gpa_history": self.semester_gpa_history,
            "semester_courses": self.semester_courses,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            major=str(data["major"]),
            enrolled_courses=data.get("enrolled_courses", {}),
            completed_courses=data.get("completed_courses", {}),
            academic_status=str(data.get("academic_status", "Good Standing")),
            semester_gpa_history=data.get("semester_gpa_history", []),
            semester_courses=data.get("semester_courses", []),
        )
