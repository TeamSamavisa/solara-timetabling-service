from dataclasses import dataclass


@dataclass()
class CourseType:
    """
    Represents the type of academic degree or program.
    
    Defines the level or category of a course (e.g., Bachelor's degree,
    Master's degree, Technical degree, Licentiate).
    
    Attributes:
        id: Unique identifier for the course type
        name: Type name (e.g., "Bachelor's", "Master's", "Technical")
    """
    id: int
    name: str
