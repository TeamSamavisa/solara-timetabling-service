def empty_space_groups_cost(groups_empty_space):
    """
    Calculates total empty space of all groups for week, maximum empty space in day and average empty space for whole
    week per group.
    :param groups_empty_space: dictionary where key = group index, values = list of rows where it is in
    :return: total cost, maximum per day, average cost
    """
    # total empty space of all groups for the whole week
    cost = 0
    # max empty space in one day for some group
    max_empty = 0

    for group_index, times in groups_empty_space.items():
        times.sort()
        # empty space for each day for current group
        empty_per_day = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

        for i in range(1, len(times) - 1):
            a = times[i-1]
            b = times[i]
            diff = b - a
            # classes are in the same day if their time div 12 is the same
            if a // 12 == b // 12 and diff > 1:
                empty_per_day[a // 12] += diff - 1
                cost += diff - 1

        # compare current max with empty spaces per day for current group
        for key, value in empty_per_day.items():
            if max_empty < value:
                max_empty = value

    # Avoid division by zero when there are no class groups
    if len(groups_empty_space) == 0:
        return 0, 0, 0.0
    
    return cost, max_empty, cost / len(groups_empty_space)


def empty_space_teachers_cost(teachers_empty_space):
    """
    Calculates total empty space of all teachers for week, maximum empty space in day and average empty space for whole
    week per teacher.
    :param teachers_empty_space: dictionary where key = name of the teacher, values = list of rows where it is in
    :return: total cost, maximum per day, average cost
    """
    # total empty space of all teachers for the whole week
    cost = 0
    # max empty space in one day for some teacher
    max_empty = 0

    for teacher_name, times in teachers_empty_space.items():
        times.sort()
        # empty space for each day for current teacher
        empty_per_day = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

        for i in range(1, len(times) - 1):
            a = times[i - 1]
            b = times[i]
            diff = b - a
            # classes are in the same day if their time div 12 is the same
            if a // 12 == b // 12 and diff > 1:
                empty_per_day[a // 12] += diff - 1
                cost += diff - 1

        # compare current max with empty spaces per day for current teacher
        for key, value in empty_per_day.items():
            if max_empty < value:
                max_empty = value

    # Avoid division by zero when there are no teachers
    if len(teachers_empty_space) == 0:
        return 0, 0, 0.0
    
    return cost, max_empty, cost / len(teachers_empty_space)


def hard_constraints_cost(matrix, data):
    """
    Calculates the total cost of hard constraints:
    - Each classroom has at most one class at a time
    - Each class is in one of its possible rooms (compatible space_type)
    - Each teacher teaches at most one class at a time
    - Each class group attends at most one class at a time
    - Teacher is available at the time (SCHEDULE_TEACHER)
    
    For everything that doesn't satisfy these constraints, one is added to the cost.
    
    Args:
        matrix: Timetable matrix [time][room] = allocation_index
        data: Timetable data (TimetableData)
        
    Returns:
        total_cost, cost_allocation, cost_teacher, cost_classrooms, cost_group
    """
    from app.models.timetable_data import TimetableData
    from app.services.optimizer import map_row_to_schedule
    
    # cost_allocation: dictionary where key = allocation index, value = total cost
    cost_allocation = {}
    for allocation_idx in data.class_allocations:
        cost_allocation[allocation_idx] = 0

    cost_classrooms = 0
    cost_teacher = 0
    cost_group = 0
    cost_teacher_availability = 0
    
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            field = matrix[i][j]  # For each slot in the matrix
            if field is not None:
                allocation1 = data.class_allocations[field]

                # Calculate cost for classroom (check if space_type is compatible)
                classroom_id = j
                if classroom_id not in allocation1.possible_classrooms:
                    cost_classrooms += 1
                    cost_allocation[field] += 1

                # Calculate cost for teacher availability (SCHEDULE_TEACHER)
                if data.teacher_schedules is not None:
                    teacher_id = allocation1.teacher.id
                    if teacher_id in data.teacher_schedules:
                        available_schedule_ids = data.teacher_schedules[teacher_id]
                        if available_schedule_ids:  # If there are defined restrictions
                            schedule_id = map_row_to_schedule(i, data.schedules)
                            if schedule_id is None or schedule_id not in available_schedule_ids:
                                cost_teacher_availability += 1
                                cost_allocation[field] += 1

                # Check conflicts with other allocations at the same time
                for k in range(j + 1, len(matrix[i])):
                    next_field = matrix[i][k]
                    if next_field is not None:
                        allocation2 = data.class_allocations[next_field]

                        # Calculate cost for teachers (same teacher, same time)
                        if allocation1.teacher.id == allocation2.teacher.id:
                            cost_teacher += 1
                            cost_allocation[field] += 1

                        # Calculate cost for class groups (same group, same time)
                        if allocation1.class_group.id == allocation2.class_group.id:
                            cost_group += 1
                            cost_allocation[field] += 1

    total_cost = cost_teacher + cost_classrooms + cost_group + cost_teacher_availability
    return total_cost, cost_allocation, cost_teacher, cost_classrooms, cost_group


def check_hard_constraints(matrix, data):
    """
    Checks if all hard constraints are satisfied and returns the number of
    overlaps with classes, rooms, teachers, class groups and availability.
    
    Args:
        matrix: Timetable matrix
        data: Timetable data (TimetableData)
        
    Returns:
        overlaps: Total number of overlaps/conflicts
    """
    from app.models.timetable_data import TimetableData
    from app.services.optimizer import map_row_to_schedule
    
    overlaps = 0
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            field = matrix[i][j]  # For each slot in the matrix
            if field is not None:
                allocation1 = data.class_allocations[field]

                # Calculate cost for classroom (incompatible space_type)
                if j not in allocation1.possible_classrooms:
                    overlaps += 1

                # Check teacher availability (SCHEDULE_TEACHER)
                if data.teacher_schedules is not None:
                    teacher_id = allocation1.teacher.id
                    if teacher_id in data.teacher_schedules:
                        available_schedule_ids = data.teacher_schedules[teacher_id]
                        if available_schedule_ids:  # If there are defined restrictions
                            schedule_id = map_row_to_schedule(i, data.schedules)
                            if schedule_id is None or schedule_id not in available_schedule_ids:
                                overlaps += 1

                # Check all other rooms at the same time
                for k in range(len(matrix[i])):
                    if k != j:
                        next_field = matrix[i][k]
                        if next_field is not None:
                            allocation2 = data.class_allocations[next_field]

                            # Calculate cost for teachers
                            if allocation1.teacher.id == allocation2.teacher.id:
                                overlaps += 1

                            # Calculate cost for class groups
                            if allocation1.class_group.id == allocation2.class_group.id:
                                overlaps += 1

    return overlaps