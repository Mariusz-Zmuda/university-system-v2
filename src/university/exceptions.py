"""
exceptions.py — Custom exception hierarchy for the University system.

All exceptions inherit from UniversityError so callers can catch the
entire family with a single except clause when needed, or target
specific errors for fine-grained handling.

Example:
    try:
        manager.enroll_student(sid, code)
    except PrerequisiteNotMetError as exc:
        print(exc)
    except UniversityError as exc:
        log.warning(exc)
"""


class UniversityError(Exception):
    """
    Base exception for all university system errors.

    Catch this to handle any domain error without caring about
    the specific subtype.
    """


class StudentNotFoundError(UniversityError):
    """Raised when a student ID does not exist in the registry."""

    def __init__(self, student_id: str) -> None:
        super().__init__(f"Student '{student_id}' not found.")


class CourseNotFoundError(UniversityError):
    """Raised when a course code does not exist in the registry."""

    def __init__(self, course_code: str) -> None:
        super().__init__(f"Course '{course_code}' not found.")


class CourseFullError(UniversityError):
    """Raised when a course has reached its maximum student capacity."""

    def __init__(self, course_code: str) -> None:
        super().__init__(f"Course '{course_code}' has reached maximum capacity.")


class PrerequisiteNotMetError(UniversityError):
    """
    Raised when a student attempts to enroll without completing
    all prerequisite courses.
    """

    def __init__(self, course_code: str, missing: list[str]) -> None:
        super().__init__(
            f"Prerequisites not met for '{course_code}'. Missing: {', '.join(missing)}."
        )


class CreditLimitExceededError(UniversityError):
    """
    Raised when enrolling in a course would push the student's
    current semester credit load above the allowed maximum.
    """

    def __init__(self, current: int, adding: int, limit: int = 18) -> None:
        super().__init__(
            f"Enrolling would exceed the {limit}-credit semester limit "
            f"(current: {current}, adding: {adding})."
        )


class DuplicateEnrollmentError(UniversityError):
    """Raised when a student attempts to enroll in a course they are already taking."""

    def __init__(self, student_id: str, course_code: str) -> None:
        super().__init__(
            f"Student '{student_id}' is already enrolled in '{course_code}'."
        )


class CourseAlreadyCompletedError(UniversityError):
    """Raised when a student attempts to re-enroll in a course they have completed."""

    def __init__(self, student_id: str, course_code: str) -> None:
        super().__init__(
            f"Student '{student_id}' has already completed '{course_code}'."
        )


class AcademicDismissalError(UniversityError):
    """
    Raised when a dismissed student attempts any enrollment action.
    Dismissal is terminal — no further enrollment is permitted.
    """

    def __init__(self, student_id: str) -> None:
        super().__init__(
            f"Student '{student_id}' has been academically dismissed and cannot enroll."
        )


class InvalidGradeError(UniversityError):
    """Raised when an unrecognised grade symbol is submitted."""

    def __init__(self, grade: str) -> None:
        super().__init__(f"Invalid grade '{grade}'. Must be one of: A, B, C, D, F.")


class DuplicateStudentError(UniversityError):
    """Raised when adding a student whose ID already exists in the registry."""

    def __init__(self, student_id: str) -> None:
        super().__init__(f"Student with ID '{student_id}' already exists.")


class DuplicateCourseError(UniversityError):
    """Raised when adding a course whose code already exists in the registry."""

    def __init__(self, course_code: str) -> None:
        super().__init__(f"Course '{course_code}' already exists.")
