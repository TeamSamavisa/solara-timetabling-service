import random
from operator import itemgetter
from typing import Dict, List, Tuple, Optional
import copy
import math
from app.models.timetable_data import TimetableData
from app.models.schedule import Schedule
from app.utils.costs import (
    check_hard_constraints, 
    hard_constraints_cost, 
    empty_space_groups_cost, 
    empty_space_teachers_cost,
)


def initial_population(data: TimetableData, matrix: List[List], free: List[Tuple[int, int]], 
                      filled: Dict[int, List[Tuple[int, int]]], 
                      groups_empty_space: Dict[int, List[int]], 
                      teachers_empty_space: Dict[int, List[int]]):
    """
    Sets up the initial timetable for classes, inserting them in free slots so that
    each class is in an appropriate room.
    
    Args:
        data: Timetable data (ASSIGNMENT, SPACE, USER, CLASS_GROUP, etc)
        matrix: Timetable matrix [time][room] = allocation_index
        free: List of free slots (time, room)
        filled: Dictionary of allocations {allocation_index: [(time, room), ...]}
        groups_empty_space: Empty spaces by class group {class_group_id: [times]}
        teachers_empty_space: Empty spaces by teacher {teacher_id: [times]}
    """
    allocations = data.class_allocations

    for index, allocation in allocations.items():
        ind = 0
        while True:
            if ind >= len(free):
                # Could not allocate this class
                print(f"Warning: Could not allocate class {index}")
                break
                
            start_field = free[ind]

            # Check if the class doesn't start on one day and end on the next
            start_time = start_field[0]
            end_time = start_time + int(allocation.duration) - 1
            if start_time % 12 > end_time % 12:
                ind += 1
                continue

            found = True
            # Check if the entire block for the class is free
            for i in range(1, int(allocation.duration)):
                field = (i + start_time, start_field[1])
                if field not in free:
                    found = False
                    ind += 1
                    break

            # Ensure the room is appropriate (check space_type)
            classroom_id = start_field[1]
            if classroom_id not in allocation.possible_classrooms:
                ind += 1
                continue

            if found:
                # Add class times for the class group
                class_group_id = allocation.class_group.id
                
                for i in range(int(allocation.duration)):
                    if class_group_id not in groups_empty_space:
                        groups_empty_space[class_group_id] = []
                    groups_empty_space[class_group_id].append(i + start_time)

                for i in range(int(allocation.duration)):
                    filled.setdefault(index, []).append((i + start_time, start_field[1]))
                    free.remove((i + start_time, start_field[1]))
                    
                    # Add class times for the teacher
                    teacher_id = allocation.teacher.id
                    if teacher_id not in teachers_empty_space:
                        teachers_empty_space[teacher_id] = []
                    teachers_empty_space[teacher_id].append(i + start_time)
                break

    # Fill the matrix
    for index, fields_list in filled.items():
        for field in fields_list:
            matrix[field[0]][field[1]] = index


def map_row_to_schedule(row: int, schedules: Dict[int, "Schedule"]) -> Optional[int]:
    """
    Maps a matrix row (time slot) to a Schedule ID.
    
    The matrix uses indices 0-59 representing:
    - 0-11: Monday (7am-6pm)
    - 12-23: Tuesday (7am-6pm)
    - 24-35: Wednesday (7am-6pm)
    - 36-47: Thursday (7am-6pm)
    - 48-59: Friday (7am-6pm)
    
    Args:
        row: Matrix row (0-59)
        schedules: Dictionary of schedules {id: Schedule}
        
    Returns:
        Corresponding schedule_id or None if not found
    """
    if not schedules:
        return None
    
    # Map index to weekday and hour
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_index = row // 12
    hour_index = row % 12
    
    if day_index >= len(days):
        return None
        
    weekday = days[day_index]
    # Assuming schedules starting at 7am
    hour = 7 + hour_index
    start_time = f"{hour:02d}:00"
    
    # Search for corresponding schedule
    for schedule_id, schedule in schedules.items():
        if (schedule.weekday == weekday and 
            schedule.start_time.startswith(f"{hour:02d}:")):
            return schedule_id
    
    return None


def exchange_two(matrix, filled, ind1, ind2):
    """
    Changes places of two classes with the same duration in timetable matrix.
    """
    fields1 = filled[ind1]
    filled.pop(ind1, None)
    fields2 = filled[ind2]
    filled.pop(ind2, None)

    for i in range(len(fields1)):
        t = matrix[fields1[i][0]][fields1[i][1]]
        matrix[fields1[i][0]][fields1[i][1]] = matrix[fields2[i][0]][fields2[i][1]]
        matrix[fields2[i][0]][fields2[i][1]] = t

    filled[ind1] = fields2
    filled[ind2] = fields1

    return matrix


def valid_teacher_group_row(matrix: List[List], data: TimetableData, 
                           allocation_index: int, row: int) -> bool:
    """
    Checks if the allocation can be at that row due to possible overlaps
    of teacher or class groups, and also if the teacher is available at this time.
    
    Args:
        matrix: Timetable matrix
        data: Timetable data
        allocation_index: Index of the allocation to check
        row: Row (time) to check
        
    Returns:
        True if there are no conflicts, False otherwise
    """
    allocation1 = data.class_allocations[allocation_index]
    
    # VALIDATION 1: Check teacher availability (SCHEDULE_TEACHER)
    if data.teacher_schedules is not None:
        teacher_id = allocation1.teacher.id
        
        # If there are schedule restrictions for this teacher
        if teacher_id in data.teacher_schedules:
            available_schedule_ids = data.teacher_schedules[teacher_id]
            
            # If there are defined restrictions (non-empty list)
            if available_schedule_ids:
                # Map matrix row to a schedule_id
                schedule_id = map_row_to_schedule(row, data.schedules)
                
                # If schedule not found or teacher not available, invalidate
                if schedule_id is None or schedule_id not in available_schedule_ids:
                    return False
    
    # VALIDATION 2: Check for teacher and class group conflicts at the same time
    for j in range(len(matrix[row])):
        if matrix[row][j] is not None:
            allocation2 = data.class_allocations[matrix[row][j]]
            
            # Check for teacher conflict
            if allocation1.teacher.id == allocation2.teacher.id:
                return False
            
            # Check for class group conflict
            if allocation1.class_group.id == allocation2.class_group.id:
                return False
                
    return True


def mutate_ideal_spot(matrix: List[List], data: TimetableData, allocation_index: int, 
                     free: List[Tuple[int, int]], filled: Dict[int, List[Tuple[int, int]]], 
                     groups_empty_space: Dict[int, List[int]], 
                     teachers_empty_space: Dict[int, List[int]]):
    """
    Tries to find new slots in the matrix for the allocation where the cost is 0
    (considering only hard constraints). If an optimal spot is found,
    the slots in the matrix are replaced.
    
    Args:
        matrix: Timetable matrix
        data: Timetable data
        allocation_index: Allocation index
        free: List of free slots
        filled: Dictionary of filled allocations
        groups_empty_space: Empty spaces by class group
        teachers_empty_space: Empty spaces by teacher
    """
    # Find rows and slots where the class currently is
    if allocation_index not in filled:
        return
        
    fields = filled[allocation_index]
    allocation = data.class_allocations[allocation_index]
    
    ind = 0
    while True:
        # Ideal spot not found, return from function
        if ind >= len(free):
            return
        start_field = free[ind]

        # Check if the class doesn't start on one day and end on the next
        start_time = start_field[0]
        end_time = start_time + int(allocation.duration) - 1
        if start_time % 12 > end_time % 12:
            ind += 1
            continue

        # Check if the new room is appropriate
        if start_field[1] not in allocation.possible_classrooms:
            ind += 1
            continue

        # Check if the entire block can be used and for possible overlaps
        found = True
        for i in range(int(allocation.duration)):
            field = (i + start_time, start_field[1])
            if field not in free or not valid_teacher_group_row(matrix, data, allocation_index, field[0]):
                found = False
                ind += 1
                break

        if found:
            # Remove current class from filled and add to free
            filled.pop(allocation_index, None)
            for f in fields:
                free.append((f[0], f[1]))
                matrix[f[0]][f[1]] = None
                
                # Remove empty space from class group at old position
                class_group_id = allocation.class_group.id
                if class_group_id in groups_empty_space and f[0] in groups_empty_space[class_group_id]:
                    groups_empty_space[class_group_id].remove(f[0])
                
                # Remove empty space from teacher at old position
                teacher_id = allocation.teacher.id
                if teacher_id in teachers_empty_space and f[0] in teachers_empty_space[teacher_id]:
                    teachers_empty_space[teacher_id].remove(f[0])

            # Add empty space for the class group
            class_group_id = allocation.class_group.id
            
            for i in range(int(allocation.duration)):
                if class_group_id not in groups_empty_space:
                    groups_empty_space[class_group_id] = []
                groups_empty_space[class_group_id].append(i + start_time)

            # Add new class time, remove slots from free and insert in matrix
            for i in range(int(allocation.duration)):
                filled.setdefault(allocation_index, []).append((i + start_time, start_field[1]))
                free.remove((i + start_time, start_field[1]))
                matrix[i + start_time][start_field[1]] = allocation_index
                
                # Add new empty space for the teacher
                teacher_id = allocation.teacher.id
                if teacher_id not in teachers_empty_space:
                    teachers_empty_space[teacher_id] = []
                teachers_empty_space[teacher_id].append(i + start_time)
            break


def evolutionary_algorithm(matrix: List[List], data: TimetableData, 
                         free: List[Tuple[int, int]], filled: Dict[int, List[Tuple[int, int]]], 
                         groups_empty_space: Dict[int, List[int]], 
                         teachers_empty_space: Dict[int, List[int]]):
    """
    Evolutionary algorithm that tries to find a timetable such that hard constraints are satisfied.
    Uses (1+1) evolutionary strategy with Schwefel's 1/5 success rule.
    
    Args:
        matrix: Timetable matrix
        data: Timetable data
        free: List of free slots
        filled: Dictionary of filled allocations
        groups_empty_space: Empty spaces by class group
        teachers_empty_space: Empty spaces by teacher
    """
    from app.utils.utils import show_timetable
    
    n = 3
    sigma = 2
    run_times = 5
    max_stagnation = 200

    for run in range(run_times):
        print(f'Run {run + 1}/{run_times} | σ = {sigma:.4f}')

        t = 0
        stagnation = 0
        cost_stats = 0
        while stagnation < max_stagnation:

            # Check if optimal solution was found
            loss_before, cost_allocations, cost_teachers, cost_classrooms, cost_groups = hard_constraints_cost(matrix, data)
            if loss_before == 0 and check_hard_constraints(matrix, data) == 0:
                print('\n✓ Optimal solution found!\n')
                show_timetable(matrix)
                break

            # Sort allocations by cost, [(cost, allocation index)]
            costs_list = sorted(cost_allocations.items(), key=itemgetter(1), reverse=True)

            # Mutation: try to improve worst allocations
            for i in range(len(costs_list) // 4):
                if random.uniform(0, 1) < sigma and costs_list[i][1] != 0:
                    mutate_ideal_spot(matrix, data, costs_list[i][0], free, filled, groups_empty_space,
                                      teachers_empty_space)

            loss_after, _, _, _, _ = hard_constraints_cost(matrix, data)
            if loss_after < loss_before:
                stagnation = 0
                cost_stats += 1
            else:
                stagnation += 1

            t += 1
            # Adapt σ for (1+1)-ES according to Schwefel's 1/5 success rule
            if t >= 10*n and t % n == 0:
                s = cost_stats
                if s < 2*n:
                    sigma *= 0.85
                else:
                    sigma /= 0.85
                cost_stats = 0

        print(f'Iterations: {t}')
        print(f'Final cost: {loss_after}')
        print(f'  - Teachers: {cost_teachers}')
        print(f'  - Class groups: {cost_groups}')
        print(f'  - Classrooms: {cost_classrooms}\n')


def simulated_hardening(matrix: List[List], data: TimetableData, 
                       free: List[Tuple[int, int]], filled: Dict[int, List[Tuple[int, int]]], 
                       groups_empty_space: Dict[int, List[int]], 
                       teachers_empty_space: Dict[int, List[int]], file: str):
    """
    Algorithm that uses simulated annealing with geometric temperature decrease to
    optimize the timetable satisfying soft constraints as much as possible
    (empty spaces for class groups).
    
    Args:
        matrix: Timetable matrix
        data: Timetable data
        free: List of free slots
        filled: Dictionary of filled allocations
        groups_empty_space: Empty spaces by class group
        teachers_empty_space: Empty spaces by teacher
        file: Output file name
    """
    from app.utils.utils import show_timetable, show_statistics
    
    # Number of iterations
    iter_count = 2500
    # Temperature
    t = 0.5
    _, _, curr_cost_group = empty_space_groups_cost(groups_empty_space)
    _, _, curr_cost_teachers = empty_space_teachers_cost(teachers_empty_space)
    curr_cost = curr_cost_group  # + curr_cost_teachers

    for i in range(iter_count):
        rt = random.uniform(0, 1)
        t *= 0.99  # Geometric temperature decrease

        # Save current results
        old_matrix = copy.deepcopy(matrix)
        old_free = copy.deepcopy(free)
        old_filled = copy.deepcopy(filled)
        old_groups_empty_space = copy.deepcopy(groups_empty_space)
        old_teachers_empty_space = copy.deepcopy(teachers_empty_space)

        # Try to mutate 1/4 of all allocations
        num_allocations = len(data.class_allocations)
        for j in range(num_allocations // 4):
            allocation_index = random.randrange(num_allocations)
            mutate_ideal_spot(matrix, data, allocation_index, free, filled, groups_empty_space, 
                            teachers_empty_space)
        
        _, _, new_cost_groups = empty_space_groups_cost(groups_empty_space)
        _, _, new_cost_teachers = empty_space_teachers_cost(teachers_empty_space)
        new_cost = new_cost_groups  # + new_cost_teachers

        if new_cost < curr_cost or rt <= math.exp((curr_cost - new_cost) / t):
            # Accept new cost and continue with new data
            curr_cost = new_cost
        else:
            # Return to previously saved data
            matrix = copy.deepcopy(old_matrix)
            free = copy.deepcopy(old_free)
            filled = copy.deepcopy(old_filled)
            groups_empty_space = copy.deepcopy(old_groups_empty_space)
            teachers_empty_space = copy.deepcopy(old_teachers_empty_space)
        
        if i % 100 == 0:
            print(f'Iteration: {i:4d} | Average cost: {curr_cost:0.8f}')

    print('\n' + '='*60)
    print('TIMETABLE AFTER ANNEALING')
    print('='*60)
    show_timetable(matrix)
    
    print('\n' + '='*60)
    print('STATISTICS AFTER ANNEALING')
    print('='*60)
    show_statistics(matrix, data, groups_empty_space, teachers_empty_space)


def optimize_timetable(timetable_data: TimetableData, output_file: str = 'timetable_solution.txt') -> Dict:
    """
    Main function to optimize the timetable using genetic algorithm.
    
    Args:
        timetable_data: Timetable data loaded from database
        output_file: Output file name to save the solution
        
    Returns:
        Dict containing the timetable matrix and statistics
        
    Data structure:
    - matrix: Matrix [time][room] = allocation_index or None
    - free: List of free slots [(time, room), ...]
    - filled: Dict {allocation_index: [(time, room), ...]}
    - groups_empty_space: Dict {class_group_id: [times]}
    - teachers_empty_space: Dict {teacher_id: [times]}
    """
    from app.utils.utils import (
        load_data_from_database,
        set_up,
        show_statistics
    )
    
    # Initialize auxiliary structures
    filled = {}
    groups_empty_space = {}
    teachers_empty_space = {}

    # Process database data
    print("Loading data from database...")
    data = load_data_from_database(timetable_data, teachers_empty_space, groups_empty_space)
    
    # Set up timetable matrix
    print(f"Setting up matrix with {len(data.classrooms)} classrooms...")
    matrix, free = set_up(len(data.classrooms))
    
    # Generate initial population
    print("Generating initial population...")
    initial_population(data, matrix, free, filled, groups_empty_space, teachers_empty_space)

    # Calculate initial cost
    total, _, _, _, _ = hard_constraints_cost(matrix, data)
    print(f'Initial hard constraints cost: {total}\n')

    # Run evolutionary algorithm
    print("Running evolutionary algorithm...")
    evolutionary_algorithm(matrix, data, free, filled, groups_empty_space, teachers_empty_space)
    
    # Display statistics
    print('\n' + '='*60)
    print('STATISTICS AFTER EVOLUTIONARY ALGORITHM')
    print('='*60)
    show_statistics(matrix, data, groups_empty_space, teachers_empty_space)
    
    # Apply simulated annealing for additional optimization
    print('\n' + '='*60)
    print('Applying simulated annealing...')
    print('='*60)
    simulated_hardening(matrix, data, free, filled, groups_empty_space, teachers_empty_space, output_file)
    
    return {
        'matrix': matrix,
        'filled': filled,
        'data': data,
        'groups_empty_space': groups_empty_space,
        'teachers_empty_space': teachers_empty_space
    }