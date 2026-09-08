import redis
import time

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

print("Scheduler started...")

while True:

    # Get tasks whose scheduled time has arrived
    tasks = r.zrangebyscore(
        "scheduled_tasks",
        0,
        time.time()
    )

    for task_id in tasks:

        task_id = str(task_id)

        # Remove task from scheduled queue
        removed = r.zrem(
            "scheduled_tasks",
            task_id
        )

        if removed == 0:
            continue

        # Get task information
        task_data = r.hgetall(
            f"task:{task_id}"
        )

        if not task_data:
            continue

        # Get priority
        priority = str(
            task_data.get("priority", "normal")
        )

        priority_values = {
            "high": 1,
            "normal": 2,
            "low": 3
        }

        priority_value = priority_values.get(
            priority,
            2
        )

        # Move task to priority queue
        r.zadd(
            "priority_queue",
            {
                task_id: priority_value
            }
        )

        # Update task status
        r.hset(
            f"task:{task_id}",
            "status",
            "PENDING"
        )

        print(
            f"Task {task_id} is now ready!"
        )

    time.sleep(1)