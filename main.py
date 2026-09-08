from fastapi import FastAPI
from pydantic import BaseModel
import redis
import uuid

app = FastAPI()

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)


class TaskRequest(BaseModel):
    task: str


@app.get("/")
def home():
    return {"message": "Task Broker is running"}


@app.post("/tasks")
def create_task(request: TaskRequest):

    task_id = str(uuid.uuid4())

    # Store task information
    r.hset(
        f"task:{task_id}",
        mapping={
            "status": "PENDING",
            "task": request.task
        }
    )

    # Add task ID to queue
    r.rpush("task_queue", task_id)

    return {
        "task_id": task_id,
        "status": "PENDING",
        "task": request.task
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: str):

    task = r.hgetall(f"task:{task_id}")

    if not task:
        return {"error": "Task not found"}

    return {
        "task_id": task_id,
        "status": task.get("status"),
        "task": task.get("task"),
        "result": task.get("result"),
        "error": task.get("error")
    }