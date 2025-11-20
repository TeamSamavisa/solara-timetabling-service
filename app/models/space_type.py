from dataclasses import dataclass


@dataclass()
class SpaceType:
    """
    Represents the type of physical space or classroom.
    
    Defines the category of a classroom based on its equipment and purpose
    (e.g., regular classroom, computer lab, chemistry lab, auditorium).
    
    Attributes:
        id: Unique identifier for the space type
        name: Type name (e.g., "Classroom", "Computer Lab", "Auditorium")
    """
    id: int
    name: str
