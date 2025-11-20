from dataclasses import dataclass
from app.models.course_type import CourseType


@dataclass()
class Course:
    """
    Represents an academic course or degree program.
    
    A course is a complete academic program that students enroll in
    (e.g., Computer Science, Software Engineering).
    
    Attributes:
        id: Unique identifier for the course
        name: Course name (e.g., "Computer Science", "Chemical Engineering")
        course_type: Type of degree (Bachelor's, Master's, etc.)
    """
    id: int
    name: str
    course_type: CourseType
