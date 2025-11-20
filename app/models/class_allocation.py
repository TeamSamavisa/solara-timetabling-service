from dataclasses import dataclass
from typing import List, Optional
from app.models.class_group import ClassGroup
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.classroom import Classroom
from app.models.schedule import Schedule


@dataclass()
class ClassAllocation:
    """Represents a class allocation in the timetable"""

    id: Optional[int]  # assignment id
    class_group: "ClassGroup"  # class group
    subject: "Subject"  # subject
    teacher: "Teacher"  # teacher
    duration: int  # in hours
    schedule: Optional["Schedule"] = None  # allocated schedule
    classroom: Optional["Classroom"] = None  # allocated classroom
    
    @property
    def possible_classrooms(self) -> List[int]:
        """Returns the classrooms compatible with the space type required by the subject"""
        # Will be filled during initialization based on the subject's space_type
        return self._possible_classrooms if hasattr(self, '_possible_classrooms') else []
    
    @possible_classrooms.setter
    def possible_classrooms(self, value: List[int]):
        self._possible_classrooms = value
