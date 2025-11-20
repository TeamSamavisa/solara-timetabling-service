import json
import random
from typing import Dict, List, Tuple
from app.models.timetable_data import TimetableData
from app.models.class_allocation import ClassAllocation
from app.utils.costs import (
    check_hard_constraints, 
    empty_space_groups_cost, 
    empty_space_teachers_cost,
)


def load_data_from_database(timetable_data: TimetableData, 
                           teachers_empty_space: Dict[int, List[int]], 
                           groups_empty_space: Dict[int, List[int]]) -> TimetableData:
    """
    Processes database data and initializes auxiliary structures.
    
    Args:
        timetable_data: Timetable data from database (TimetableData)
        teachers_empty_space: Empty spaces by teacher {teacher_id: [times]}
        groups_empty_space: Empty spaces by class group {class_group_id: [times]}
        
    Returns:
        Processed and initialized TimetableData
    """
    # Initialize auxiliary structures for teachers
    for teacher_id in timetable_data.teachers.keys():
        if teacher_id not in teachers_empty_space:
            teachers_empty_space[teacher_id] = []

    # Initialize auxiliary structures for class groups
    for class_group_id in timetable_data.class_groups.keys():
        if class_group_id not in groups_empty_space:
            groups_empty_space[class_group_id] = []

    # For each allocation, determine possible classrooms based on space_type
    for allocation_idx, allocation in timetable_data.class_allocations.items():
        required_space_type_id = allocation.subject.required_space_type.id
        
        # Find classrooms compatible with the required space_type
        possible_classroom_ids = []
        for classroom_idx, classroom in timetable_data.classrooms.items():
            if classroom.space_type.id == required_space_type_id and not classroom.blocked:
                possible_classroom_ids.append(classroom_idx)
        
        allocation.possible_classrooms = possible_classroom_ids

    return timetable_data


def set_up(num_of_classrooms: int, num_of_time_slots: int = 60) -> Tuple[List[List], List[Tuple[int, int]]]:
    """
    Sets up the timetable matrix and the list of free slots.
    
    Args:
        num_of_classrooms: Number of classrooms (columns)
        num_of_time_slots: Number of time slots (rows). 
                          Default: 60 = 5 days * 12 hours per day
        
    Returns:
        matrix: Matrix [time][room] = allocation_index or None
        free: List of tuples (time, room) representing free slots
    """
    width, height = num_of_classrooms, num_of_time_slots
    matrix = [[None for x in range(width)] for y in range(height)]
    free = []

    # initialise free dict as all the fields from matrix
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            free.append((i, j))
    
    return matrix, free


def show_timetable(matrix: List[List]):
    """
    Displays the timetable matrix.
    
    Args:
        matrix: Timetable matrix [time][room] = allocation_index
    """
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]  # Typical university hours

    # print heading for classrooms
    for i in range(len(matrix[0])):
        if i == 0:
            print('{:17s} S{:6s}'.format('', '0'), end='')
        else:
            print('S{:6s}'.format(str(i)), end='')
    print()

    day_cnt = 0
    hour_cnt = 0
    for i in range(len(matrix)):
        if hour_cnt < len(hours):
            day = days[day_cnt] if day_cnt < len(days) else f'Dia {day_cnt}'
            hour = hours[hour_cnt]
            print('{:10s} {:2d}h ->  '.format(day, hour), end='')
            for j in range(len(matrix[i])):
                print('{:6s} '.format(str(matrix[i][j]) if matrix[i][j] is not None else '-'), end='')
            print()
        
        hour_cnt += 1
        if hour_cnt >= 12:  # 12 slots por dia
            hour_cnt = 0
            day_cnt += 1
            print()

def show_statistics(matrix: List[List], data: TimetableData, 
                   groups_empty_space: Dict[int, List[int]], 
                   teachers_empty_space: Dict[int, List[int]]):
    """
    Displays statistics about the generated timetable.
    
    Args:
        matrix: Timetable matrix
        data: Timetable data
        groups_empty_space: Empty spaces by class group
        teachers_empty_space: Empty spaces by teacher
    """
    cost_hard = check_hard_constraints(matrix, data)
    if cost_hard == 0:
        print('✓ Hard constraints satisfied: 100.00%')
    else:
        print(f'✗ Hard constraints NOT satisfied, cost: {cost_hard}')

    empty_groups, max_empty_group, average_empty_groups = empty_space_groups_cost(groups_empty_space)
    print(f'Empty spaces CLASS GROUPS (total): {empty_groups}')
    print(f'Maximum empty space CLASS GROUP (per day): {max_empty_group}')
    print(f'Average empty space CLASS GROUPS (per week): {average_empty_groups:.02f}\n')

    empty_teachers, max_empty_teacher, average_empty_teachers = empty_space_teachers_cost(teachers_empty_space)
    print(f'Empty spaces TEACHERS (total): {empty_teachers}')
    print(f'Maximum empty space TEACHER (per day): {max_empty_teacher}')
    print(f'Average empty space TEACHERS (per week): {average_empty_teachers:.02f}\n')
