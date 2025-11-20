from dataclasses import dataclass
from typing import Dict, List
from app.models.class_allocation import ClassAllocation
from app.models.class_group import ClassGroup
from app.models.classroom import Classroom
from app.models.teacher import Teacher
from app.models.schedule import Schedule


@dataclass()
class TimetableData:
    """
    Container for all data required by the timetable optimization algorithm.
    
    This structure holds all entities and relationships needed to generate
    an optimized academic timetable, including class allocations, classrooms,
    teachers, class groups, and schedule constraints.
    
    Attributes:
        class_allocations: Map of allocation index to ClassAllocation objects
                          Represents classes that need to be scheduled
        classrooms: Map of classroom ID to Classroom objects
                   Available physical spaces for classes
        teachers: Map of teacher ID to Teacher objects
                 Instructors who teach classes
        class_groups: Map of class group ID to ClassGroup objects
                     Student groups that attend classes together
        schedules: Map of schedule ID to Schedule objects
                  Available time slots during the week
        teacher_schedules: Optional map of teacher ID to list of available schedule IDs
                          Defines when each teacher is available (SCHEDULE_TEACHER table)
        subject_teachers: Optional map of subject ID to list of qualified teacher IDs
                         Defines which teachers can teach each subject (SUBJECT_TEACHER table)
    """

    class_allocations: Dict[int, ClassAllocation]  # index -> allocation (ASSIGNMENT)
    classrooms: Dict[int, "Classroom"]  # id -> classroom (SPACE)
    teachers: Dict[int, "Teacher"]  # id -> teacher (USER)
    class_groups: Dict[int, "ClassGroup"]  # id -> class_group (CLASS_GROUP)
    schedules: Dict[int, "Schedule"]  # id -> schedule (SCHEDULE)
    
    # Auxiliary structures for optimization
    teacher_schedules: Dict[int, List[int]] = None  # teacher_id -> [schedule_ids] (SCHEDULE_TEACHER)
    subject_teachers: Dict[int, List[int]] = None  # subject_id -> [teacher_ids] (SUBJECT_TEACHER)
