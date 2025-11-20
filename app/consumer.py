import json
import logging
import pika
import time
from typing import Dict, Any

from config.settings import get_rabbitmq_config
from app.services.optimizer import optimize_timetable
from app.models.timetable_data import TimetableData
from app.models.class_allocation import ClassAllocation
from app.models.class_group import ClassGroup
from app.models.classroom import Classroom
from app.models.teacher import Teacher
from app.models.subject import Subject
from app.models.course import Course
from app.models.course_type import CourseType
from app.models.shift import Shift
from app.models.space_type import SpaceType
from app.models.schedule import Schedule

logger = logging.getLogger(__name__)


def parse_timetable_data(data: Dict[str, Any]) -> TimetableData:
    """
    Converts JSON data received from RabbitMQ into TimetableData structure.
    
    Args:
        data: Dictionary with timetable data from database
        
    Expected format:
    {
        "space_types": [{"id": 1, "name": "Sala de Aula"}, ...],
        "classrooms": [{"id": 1, "name": "Sala 101", "floor": 1, "capacity": 40, 
                       "blocked": false, "space_type_id": 1}, ...],
        "course_types": [{"id": 1, "name": "Bacharelado"}, ...],
        "courses": [{"id": 1, "name": "Ciência da Computação", "course_type_id": 1}, ...],
        "shifts": [{"id": 1, "name": "Matutino"}, ...],
        "teachers": [{"id": 1, "full_name": "Prof. João Silva"}, ...],
        "subjects": [{"id": 1, "name": "Algoritmos", "required_space_type_id": 1}, ...],
        "schedules": [{"id": 1, "weekday": "Monday", "start_time": "07:00", "end_time": "08:00"}, ...],
        "class_groups": [{"id": 1, "name": "CC-2024.1-M", "course_id": 1, 
                         "shift_id": 1, "student_count": 35}, ...],
        "class_allocations": [{"id": 1, "class_group_id": 1, "subject_id": 1, 
                              "teacher_id": 1, "duration": 2}, ...],
        "teacher_schedules": {"1": [1, 2, 3, ...], "2": [4, 5, 6, ...]},
        "subject_teachers": {"1": [1, 2], "2": [3]}
    }
    
    Returns:
        Processed TimetableData
    """
    # Parse SpaceTypes
    space_types = {}
    for st in data.get("space_types", []):
        space_types[st["id"]] = SpaceType(
            id=st["id"],
            name=st["name"]
        )
    
    # Parse Classrooms
    classrooms = {}
    for room in data.get("classrooms", []):
        classrooms[room["id"]] = Classroom(
            id=room["id"],
            name=room["name"],
            floor=room["floor"],
            capacity=room["capacity"],
            blocked=room.get("blocked", False),
            space_type=space_types[room["space_type_id"]]
        )
    
    # Parse CourseTypes
    course_types = {}
    for ct in data.get("course_types", []):
        course_types[ct["id"]] = CourseType(
            id=ct["id"],
            name=ct["name"]
        )
    
    # Parse Courses
    courses = {}
    for course in data.get("courses", []):
        courses[course["id"]] = Course(
            id=course["id"],
            name=course["name"],
            course_type=course_types[course["course_type_id"]]
        )
    
    # Parse Shifts
    shifts = {}
    for shift in data.get("shifts", []):
        shifts[shift["id"]] = Shift(
            id=shift["id"],
            name=shift["name"]
        )
    
    # Parse Schedules FIRST (needed by teachers)
    schedules = {}
    for schedule in data.get("schedules", []):
        schedules[schedule["id"]] = Schedule(
            id=schedule["id"],
            weekday=schedule["weekday"],
            start_time=schedule["start_time"],
            end_time=schedule["end_time"]
        )
    
    # Parse Subjects (needs courses and space_types, but NOT teachers yet)
    subjects = {}
    for subject in data.get("subjects", []):
        subjects[subject["id"]] = Subject(
            id=subject["id"],
            name=subject["name"],
            required_space_type=space_types[subject["required_space_type_id"]],
            course=courses[subject["course_id"]]
        )
    
    # Parse Teachers (needs schedules and subjects)
    teachers = {}
    teacher_schedules_map = data.get("teacher_schedules", {})
    subject_teachers_map = data.get("subject_teachers", {})
    
    for teacher in data.get("teachers", []):
        teacher_id = teacher["id"]
        
        # Get schedules for this teacher
        teacher_schedule_ids = teacher_schedules_map.get(str(teacher_id), [])
        teacher_schedule_objs = [schedules[sid] for sid in teacher_schedule_ids if sid in schedules]
        
        # Get subjects for this teacher (inverse mapping)
        teacher_subject_objs = []
        for subject_id, teacher_ids in subject_teachers_map.items():
            if teacher_id in teacher_ids:
                subject_id_int = int(subject_id)
                if subject_id_int in subjects:
                    teacher_subject_objs.append(subjects[subject_id_int])
        
        teachers[teacher_id] = Teacher(
            id=teacher_id,
            full_name=teacher["full_name"],
            schedules=teacher_schedule_objs,
            subjects=teacher_subject_objs
        )
    
    # Parse ClassGroups
    class_groups = {}
    for group in data.get("class_groups", []):
        class_groups[group["id"]] = ClassGroup(
            id=group["id"],
            name=group["name"],
            semester=group.get("semester", "2024.1"),  # Default if not provided
            module=group.get("module", "1"),  # Default if not provided
            student_count=group["student_count"],
            course=courses[group["course_id"]],
            shift=shifts[group["shift_id"]]
        )
    
    # Parse ClassAllocations
    class_allocations = {}
    for idx, allocation in enumerate(data.get("class_allocations", [])):
        class_allocations[idx] = ClassAllocation(
            id=allocation.get("id"),
            class_group=class_groups[allocation["class_group_id"]],
            subject=subjects[allocation["subject_id"]],
            teacher=teachers[allocation["teacher_id"]],
            duration=allocation["duration"]
        )
    
    # Parse auxiliary structures
    teacher_schedules = None
    if "teacher_schedules" in data:
        teacher_schedules = {
            int(k): v for k, v in data["teacher_schedules"].items()
        }
    
    subject_teachers = None
    if "subject_teachers" in data:
        subject_teachers = {
            int(k): v for k, v in data["subject_teachers"].items()
        }
    
    return TimetableData(
        class_allocations=class_allocations,
        classrooms=classrooms,
        teachers=teachers,
        class_groups=class_groups,
        schedules=schedules,
        teacher_schedules=teacher_schedules,
        subject_teachers=subject_teachers
    )


def process_optimize_timetable(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes timetable optimization request.
    
    Args:
        data: Timetable data to optimize
        
    Returns:
        Dictionary with optimization result
    """
    try:
        logger.info("Starting timetable optimization...")
        
        # Parse data to TimetableData
        timetable_data = parse_timetable_data(data)
        
        logger.info(f"Data parsed: {len(timetable_data.class_allocations)} allocations, "
                   f"{len(timetable_data.classrooms)} classrooms, "
                   f"{len(timetable_data.teachers)} teachers")
        
        # Execute optimization
        result = optimize_timetable(timetable_data)
        
        # Convert result to JSON-serializable format
        matrix = result['matrix']
        filled = result['filled']
        
        # Format result for return
        optimized_schedule = []
        for allocation_idx, time_slots in filled.items():
            allocation = timetable_data.class_allocations[allocation_idx]
            
            if time_slots:
                classroom_idx = time_slots[0][1]
                classroom = timetable_data.classrooms[classroom_idx]
                
                # Map time to day and hour
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                hours = list(range(7, 19))  # 7am-6pm
                
                time_info = []
                for time_slot in time_slots:
                    row = time_slot[0]
                    day_idx = row // 12
                    hour_idx = row % 12
                    
                    if day_idx < len(days) and hour_idx < len(hours):
                        time_info.append({
                            "day": days[day_idx],
                            "hour": hours[hour_idx]
                        })
                
                optimized_schedule.append({
                    "allocation_id": allocation.id,
                    "class_group": {
                        "id": allocation.class_group.id,
                        "name": allocation.class_group.name,
                        "course": allocation.class_group.course.name,
                        "shift": allocation.class_group.shift.name
                    },
                    "subject": {
                        "id": allocation.subject.id,
                        "name": allocation.subject.name
                    },
                    "teacher": {
                        "id": allocation.teacher.id,
                        "name": allocation.teacher.full_name
                    },
                    "classroom": {
                        "id": classroom.id,
                        "name": classroom.name,
                        "floor": classroom.floor
                    },
                    "time_slots": time_info,
                    "duration": allocation.duration
                })
        
        # Calculate statistics
        from app.utils.costs import check_hard_constraints
        hard_constraints_cost = check_hard_constraints(matrix, timetable_data)
        
        empty_groups = result.get('groups_empty_space', {})
        empty_teachers = result.get('teachers_empty_space', {})
        
        from app.utils.costs import empty_space_groups_cost, empty_space_teachers_cost
        groups_cost, max_empty_group, avg_empty_groups = empty_space_groups_cost(empty_groups)
        teachers_cost, max_empty_teacher, avg_empty_teachers = empty_space_teachers_cost(empty_teachers)
        
        logger.info(f"Optimization completed. Cost: {hard_constraints_cost}")
        
        return {
            "status": "success",
            "message": "Timetable optimized successfully",
            "data": {
                "schedule": optimized_schedule,
                "statistics": {
                    "hard_constraints_satisfied": hard_constraints_cost == 0,
                    "hard_constraints_cost": hard_constraints_cost,
                    "total_allocations": len(timetable_data.class_allocations),
                    "groups_empty_space": {
                        "total": groups_cost,
                        "max_per_day": max_empty_group,
                        "average_per_week": avg_empty_groups
                    },
                    "teachers_empty_space": {
                        "total": teachers_cost,
                        "max_per_day": max_empty_teacher,
                        "average_per_week": avg_empty_teachers
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error optimizing timetable: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error optimizing timetable: {str(e)}"
        }


def callback(ch, method, properties, body):
    """Message callback - acknowledges quickly and processes asynchronously"""
    correlation_id = properties.correlation_id

    try:
        logger.info(f"Received message: {correlation_id}")
        message = json.loads(body)
        command = message.get("pattern")

        if command == "test_connection":
            result = {"status": "success", "message": "Connection established"}

            # Send response and acknowledge immediately
            if properties.reply_to:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=correlation_id),
                    body=json.dumps(result),
                )

        elif command == "optimize_timetable":
            logger.info("Processing optimize_timetable request")
            
            # Extract data from message
            timetable_data = message.get("data", {})
            
            # Process optimization
            result = process_optimize_timetable(timetable_data)
            
            # Send response
            if properties.reply_to:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=correlation_id),
                    body=json.dumps(result),
                )
                logger.info(f"Response sent for correlation_id: {correlation_id}")

        else:
            result = {"status": "error", "message": f"Unknown command: {command}"}

            if properties.reply_to:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=correlation_id),
                    body=json.dumps(result),
                )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message: {e}")

    except Exception as e:
        logger.error(f"Unexpected error in callback: {e}", exc_info=True)

    finally:
        # Acknowledge the message (except for process_assignments which is handled above)
        try:
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.warning(f"Error acknowledging message: {e}")


def create_connection_and_channel(rabbitmq_config):
    """Create RabbitMQ connection and channel with proper configuration"""
    connection_params = pika.ConnectionParameters(
        host=rabbitmq_config["host"],
        port=rabbitmq_config["port"],
        virtual_host=rabbitmq_config["vhost"],
        credentials=pika.PlainCredentials(
            username=rabbitmq_config["username"], password=rabbitmq_config["password"]
        ),
        heartbeat=rabbitmq_config["heartbeat"],
        blocked_connection_timeout=300,
        socket_timeout=10,
        connection_attempts=3,
        retry_delay=2,
    )

    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()

    # Configure channel
    queue_name = rabbitmq_config["queue_name"]
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    return connection, channel, queue_name


def start_consumer():
    """Start the RabbitMQ consumer with improved reconnection logic"""
    rabbitmq_config = get_rabbitmq_config()
    max_reconnect_attempts = 10
    reconnect_delay = 5
    current_attempt = 0

    while current_attempt < max_reconnect_attempts:
        connection = None
        channel = None

        try:
            logger.info(
                f"Starting consumer (attempt {current_attempt + 1}/{max_reconnect_attempts})"
            )

            connection, channel, queue_name = create_connection_and_channel(
                rabbitmq_config
            )

            # Reset attempt counter on successful connection
            current_attempt = 0

            channel.basic_consume(queue=queue_name, on_message_callback=callback)

            logger.info(f"Consumer started, listening on queue: {queue_name}")
            channel.start_consuming()

        except pika.exceptions.StreamLostError as e:
            logger.error(
                f"Connection lost: {e}. Attempt {current_attempt + 1}/{max_reconnect_attempts}"
            )
            current_attempt += 1

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(
                f"AMQP Connection error: {e}. Attempt {current_attempt + 1}/{max_reconnect_attempts}"
            )
            current_attempt += 1

        except KeyboardInterrupt:
            logger.info("Shutdown signal received, stopping consumer...")
            break

        except Exception as e:
            logger.error(
                f"Unexpected error: {e}. Attempt {current_attempt + 1}/{max_reconnect_attempts}",
                exc_info=True,
            )
            current_attempt += 1

        finally:
            # Clean up connections
            try:
                if channel and not channel.is_closed:
                    channel.stop_consuming()
                    channel.close()
            except Exception as e:
                logger.warning(f"Error closing channel: {e}")

            try:
                if connection and not connection.is_closed:
                    connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

        if current_attempt < max_reconnect_attempts:
            logger.info(f"Reconnecting in {reconnect_delay} seconds...")
            time.sleep(reconnect_delay)
            # Exponential backoff with max delay of 60 seconds
            reconnect_delay = min(reconnect_delay * 1.5, 60)

    logger.error(
        f"Max reconnection attempts ({max_reconnect_attempts}) reached. Exiting."
    )


if __name__ == "__main__":
    start_consumer()
