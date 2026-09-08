import redis
import uuid
import time

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

task_name = input("Enter task name: ")
priority = input("Enter priority (high/normal/low): ").lower()

priority_values = {
    "high": 1,
    "normal": 2,
    "low": 3
}

if priority not in priority_values:
    print("Invalid priority!")
    exit()

delay = int(
    input("Run task after how many seconds? ")
)

task_id = str(uuid.uuid4())

scheduled_time = time.time() + delay

# Store task
r.hset(
    f"task:{task_id}",
    mapping={
        "status": "SCHEDULED",
        "task": task_name,
        "priority": priority,
        "retries": "0"
    }
)

# Add to scheduled tasks
r.zadd(
    "scheduled_tasks",
    {
        task_id: scheduled_time
    }
)

print("Scheduled task created!")
print(f"Task ID: {task_id}")
print(f"Runs after: {delay} seconds")
print(f"Priority: {priority}")