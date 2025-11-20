from dataclasses import dataclass
from app.models.course import Course
from app.models.shift import Shift


@dataclass()
class ClassGroup:
    """
    Represents a class group (turma) in the timetable system.
    
    A class group is a collection of students enrolled in the same course,
    semester, and shift. They attend classes together.
    
    Attributes:
        id: Unique identifier for the class group
        name: Display name (e.g., "CC-2024.1-M")
        semester: Academic semester (e.g., "2024.1", "2024.2")
        module: Course module/period (e.g., "1", "2", "3")
        student_count: Number of students in the group
        course: The course this group belongs to
        shift: The time shift (morning, afternoon, evening, etc.)
    """
    id: int
    name: str
    semester: str
    module: str
    student_count: int
    course: Course
    shift: Shift
