from dataclasses import dataclass


@dataclass()
class Schedule:
    """
    Represents a time slot in the weekly schedule.
    
    Defines a specific period during the week when classes can be scheduled.
    Each schedule represents one hour slot.
    
    Attributes:
        id: Unique identifier for the schedule slot
        weekday: Day of the week (Monday, Tuesday, Wednesday, Thursday, Friday)
        start_time: Start time in HH:MM format (e.g., "07:00", "14:00")
        end_time: End time in HH:MM format (e.g., "08:00", "15:00")
    """
    id: int
    weekday: str
    start_time: str
    end_time: str
