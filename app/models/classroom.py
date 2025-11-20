from dataclasses import dataclass
from app.models.space_type import SpaceType


@dataclass
class Classroom:
    """
    Represents a physical classroom or learning space.
    
    Each classroom has a specific type (regular room, lab, auditorium, etc.)
    and can be temporarily blocked for maintenance or other reasons.
    
    Attributes:
        id: Unique identifier for the classroom
        name: Display name (e.g., "Room 101", "Lab Info 201")
        floor: Floor number where the classroom is located
        capacity: Maximum number of students that can fit
        blocked: Whether the classroom is unavailable (maintenance, etc.)
        space_type: Type of space (classroom, lab, auditorium, etc.)
    """
    id: int
    name: str
    floor: int
    capacity: int
    blocked: bool
    space_type: SpaceType
