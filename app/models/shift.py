from dataclasses import dataclass


@dataclass()
class Shift:
    """
    Represents a time shift for class groups.
    
    Defines the general time period when a class group has classes
    (e.g., morning, afternoon, evening, full-time).
    
    Attributes:
        id: Unique identifier for the shift
        name: Shift name (e.g., "Morning", "Afternoon", "Evening", "Full-time")
    """
    id: int
    name: str
