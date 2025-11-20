from dataclasses import dataclass
from app.models.course import Course
from app.models.space_type import SpaceType


@dataclass()
class Subject:
    """
    Represents an academic subject or discipline.
    
    A subject is a specific course unit that students take as part of their
    degree program. Each subject requires a specific type of classroom.
    
    Attributes:
        id: Unique identifier for the subject
        name: Subject name (e.g., "Algorithms", "Database", "Organic Chemistry")
        required_space_type: Type of classroom needed (lab, regular room, etc.)
        course: The degree program this subject belongs to
    """
    id: int
    name: str
    required_space_type: SpaceType
    course: Course
