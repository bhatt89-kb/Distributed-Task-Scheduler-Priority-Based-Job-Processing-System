import redis
import uuid

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

# Get task name
task_name = input("Enter task name: ")

# Get priority
priority = input("Enter priority (high/normal/low): ").lower()

# Convert priority to a number
priority_values = {
    "high": 1,
    "normal": 2,
    "low": 3
}

if priority not in priority_values:
    print("Invalid priority!")
    exit()

priority_value = priority_values[priority]

# Create unique task ID
task_id = str(uuid.uuid4())

# Store task information
r.hset(
    f"task:{task_id}",
    mapping={
        "status": "PENDING",
        "task": task_name,
        "priority": priority,
        "retries": 0
    }
)

# Add task to priority queue
r.zadd(
    "priority_queue",
    {task_id: priority_value}
)

print("Task added to queue!")
print(f"Task ID: {task_id}")
print(f"Priority: {priority}")