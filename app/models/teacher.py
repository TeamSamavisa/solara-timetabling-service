from dataclasses import dataclass
from typing import List
from app.models.schedule import Schedule
from app.models.subject import Subject


@dataclass()
class Teacher:
    """
    Represents a teacher or instructor.
    
    A teacher can teach multiple subjects and has availability constraints
    based on their schedule preferences.
    
    Attributes:
        id: Unique identifier for the teacher
        full_name: Teacher's full name (e.g., "Prof. John Smith")
        schedules: List of time slots when the teacher is available
        subjects: List of subjects the teacher is qualified to teach
    """
    id: int
    full_name: str
    schedules: List[Schedule]
    subjects: List[Subject]
