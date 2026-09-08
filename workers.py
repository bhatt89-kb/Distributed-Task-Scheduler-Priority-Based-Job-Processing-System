import redis
import time
from task_handlers import execute_task

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
    socket_timeout=None
)

MAX_RETRIES = 3

print("Worker started...")

while True:

    # Get the highest-priority task
    tasks = r.zrange("priority_queue", 0, 0)

    if not tasks:
        time.sleep(1)
        continue

    # Convert Redis value to string
    task_id = str(tasks[0])

    # Remove the task from priority queue
    removed = r.zrem("priority_queue", task_id)

    if removed == 0:
        continue

    # Get task information
    task_data = r.hgetall(f"task:{task_id}")

    if not task_data:
        print(f"Task {task_id} not found!")
        continue

    task_name = str(task_data.get("task", "unknown"))

    retries = int(task_data.get("retries", "0"))

    priority = str(task_data.get("priority", "normal"))

    print(f"Processing: {task_name}")
    print(f"Priority: {priority}")
    print(f"Attempt: {retries + 1}")

    # Mark task as RUNNING
    r.hset(
        f"task:{task_id}",
        "status",
        "RUNNING"
    )

    try:

        # Execute the task
        result = execute_task(task_name)

        # Mark task as completed
        r.hset(
            f"task:{task_id}",
            mapping={
                "status": "COMPLETED",
                "result": str(result)
            }
        )

        print(f"Task completed: {result}")

    except Exception as e:

        retries += 1

        if retries < MAX_RETRIES:

            # Update retry information
            r.hset(
                f"task:{task_id}",
                mapping={
                    "status": "RETRYING",
                    "retries": str(retries),
                    "error": str(e)
                }
            )

            # Priority values
            priority_values = {
                "high": 1,
                "normal": 2,
                "low": 3
            }

            priority_value = priority_values.get(priority, 2)

            # Put task back into priority queue
            r.zadd(
                "priority_queue",
                {
                    task_id: priority_value
                }
            )

            print(
                f"Task failed. Retrying... Attempt {retries + 1}"
            )

        else:

            # Permanently failed
            r.hset(
                f"task:{task_id}",
                mapping={
                    "status": "FAILED",
                    "retries": str(retries),
                    "error": str(e)
                }
            )

            print("Task permanently failed!")