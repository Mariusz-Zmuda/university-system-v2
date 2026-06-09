"""
course.py — Course model.

Responsibilities:
- Track enrolled students and capacity
- Provide analytics: average grade, pass rate, top students
- Generate formatted course reports
"""

from university.models.student import GRADE_POINTS


class Course:
    """
    Represents a university course.

    Attributes:
        course_code:       Unique identifier e.g. COMP1001
        title:             Human-readable course name
        credits:           Credit value for the course (e.g. 3 or 4)
        max_capacity:      Maximum number of students
        prerequisites:     List of course codes that must be completed first
        enrolled_students: List of student IDs currently enrolled
    """

    def __init__(
        self,
        course_code: str,
        title: str,
        credits: int,
        max_capacity: int,
        prerequisites: list[str] | None = None,
        enrolled_students: list[str] | None = None,
    ) -> None:
        self.course_code = course_code
        self.title = title
        self.credits = credits
        self.max_capacity = max_capacity
        self.prerequisites: list[str] = prerequisites or []
        self.enrolled_students: list[str] = enrolled_students or []

    # ------------------------------------------------------------------
    # Enrollment management
    # ------------------------------------------------------------------

    def add_student(self, student_id: str) -> None:
        """Add a student. No-op if already enrolled (prevents duplicates)."""
        if student_id not in self.enrolled_students:
            self.enrolled_students.append(student_id)

    def remove_student(self, student_id: str) -> None:
        """Remove a student. No-op if not present."""
        if student_id in self.enrolled_students:
            self.enrolled_students.remove(student_id)

    def is_full(self) -> bool:
        """Return True if at maximum capacity."""
        return len(self.enrolled_students) >= self.max_capacity

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def course_average(self, student_registry: dict) -> float:
        """Mean GPA points across all graded students."""
        points = [
            GRADE_POINTS[s.completed_courses[self.course_code]]
            for sid in self.enrolled_students
            if (s := student_registry.get(sid))
            and self.course_code in s.completed_courses
        ]
        return round(sum(points) / len(points), 2) if points else 0.0

    def pass_rate(self, student_registry: dict) -> float:
        """Percentage of graded students who passed (grade not F)."""
        graded = [
            s.completed_courses[self.course_code]
            for sid in self.enrolled_students
            if (s := student_registry.get(sid))
            and self.course_code in s.completed_courses
        ]
        if not graded:
            return 0.0
        passed = sum(1 for g in graded if g != "F")
        return round((passed / len(graded)) * 100, 1)

    def top_students(
        self,
        student_registry: dict,
        n: int = 3,
    ) -> list[tuple[str, str, str]]:
        """Return top-n students as (student_id, name, grade), best first."""
        results = [
            (
                GRADE_POINTS[s.completed_courses[self.course_code]],
                sid,
                s.name,
                s.completed_courses[self.course_code],
            )
            for sid in self.enrolled_students
            if (s := student_registry.get(sid))
            and self.course_code in s.completed_courses
        ]
        results.sort(reverse=True, key=lambda x: x[0])
        return [(sid, name, grade) for _, sid, name, grade in results[:n]]

    def get_course_report(self, student_registry: dict) -> str:
        """Generate a formatted course analytics report."""
        avg = self.course_average(student_registry)
        rate = self.pass_rate(student_registry)
        top = self.top_students(student_registry)

        lines: list[str] = [
            "=" * 44,
            f"  COURSE REPORT: {self.course_code}",
            "=" * 44,
            f"Title        : {self.title}",
            f"Credits      : {self.credits}",
            f"Enrolment    : {len(self.enrolled_students)}/{self.max_capacity}",
            f"Prerequisites: {', '.join(self.prerequisites) or 'None'}",
            "-" * 44,
            f"Average GPA  : {avg:.2f}",
            f"Pass Rate    : {rate:.1f}%",
            "-" * 44,
            "Top Students :",
        ]
        if top:
            for rank, (sid, name, grade) in enumerate(top, 1):
                lines.append(f"  {rank}. {name} ({sid}) — {grade}")
        else:
            lines.append("  No graded students yet.")
        lines.append("=" * 44)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "course_code": self.course_code,
            "title": self.title,
            "credits": self.credits,
            "max_capacity": self.max_capacity,
            "prerequisites": self.prerequisites,
            "enrolled_students": self.enrolled_students,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Course":
        return cls(
            course_code=str(data["course_code"]),
            title=str(data["title"]),
            credits=int(str(data["credits"])),
            max_capacity=int(str(data["max_capacity"])),
            prerequisites=data.get("prerequisites", []),
            enrolled_students=data.get("enrolled_students", []),
        )

    def __repr__(self) -> str:
        return (
            f"Course(code={self.course_code!r}, "
            f"title={self.title!r}, credits={self.credits})"
        )
