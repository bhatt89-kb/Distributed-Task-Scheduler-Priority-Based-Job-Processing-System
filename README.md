# Distributed Task Scheduler & Processing System

A lightweight distributed task-processing system built with **Python, FastAPI, Redis, and Docker**.

The project demonstrates how tasks can be created, stored, scheduled, prioritized, processed by workers, and tracked through different execution states.

> **Project status:** This is an educational/prototype implementation focused on understanding task queues, scheduling, workers, Redis state management, retries, and distributed processing concepts.

---

## 1. Overview

The system is designed around a simple idea:

**Create a task → store its state → place it in a queue → process it with a worker → update the result/status.**

It supports two ways of creating tasks:

1. **Immediate tasks** through the FastAPI broker or `producers.py`
2. **Scheduled tasks** through `scheduled_producer.py`, which are released by `scheduler.py` when their execution time arrives

Workers consume tasks from the priority queue and execute them using predefined task handlers.

---

## 2. Architecture

```text
                         ┌──────────────────────┐
                         │       Client         │
                         │  API / Producer      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     Task Broker      │
                         │      FastAPI         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                  ┌──────────────────────────────────┐
                  │              Redis               │
                  │                                  │
                  │  Task State / Task Metadata      │
                  │  Priority Queue                  │
                  │  Scheduled Tasks                 │
                  └──────────────┬───────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
        ┌────────────────┐              ┌────────────────┐
        │    Scheduler   │              │    Workers     │
        │                │              │                │
        │ Releases tasks │              │ Execute tasks  │
        │ when due       │              │ + retry logic  │
        └───────┬────────┘              └───────┬────────┘
                │                               │
                └──────────► Redis ◄────────────┘
                                │
                                ▼
                       Task Status / Result
```

---

## 3. Main Components

### Task Broker - `main.py`

The FastAPI application acts as the API layer for the system.

It currently provides:

- `GET /` - checks whether the broker is running
- `POST /tasks` - creates an immediate task
- `GET /tasks/{task_id}` - retrieves task information and execution state

When a task is created, the broker:

1. Generates a unique task ID
2. Stores task information in Redis
3. Sets the initial status to `PENDING`
4. Adds the task ID to `task_queue`

### Producer - `producers.py`

The producer provides a command-line way to create prioritized tasks.

The user selects:

- Task name
- Priority: `high`, `normal`, or `low`

Priority is represented numerically:

| Priority | Redis Score |
|---|---:|
| High | 1 |
| Normal | 2 |
| Low | 3 |

Tasks are stored in Redis and added to the `priority_queue` sorted set.

### Scheduled Producer - `scheduled_producer.py`

This component creates tasks that should run in the future.

The user provides:

- Task name
- Priority
- Delay in seconds

The task is stored with status:

```text
SCHEDULED
```

and placed in the Redis `scheduled_tasks` sorted set using its scheduled execution timestamp.

### Scheduler - `scheduler.py`

The scheduler continuously checks Redis for scheduled tasks whose execution time has arrived.

Its job is **not to execute the task**.

Instead, it:

1. Finds due scheduled tasks
2. Removes them from `scheduled_tasks`
3. Reads their metadata
4. Places them into the `priority_queue`
5. Changes their status from `SCHEDULED` to `PENDING`

This creates a separation between:

```text
When should the task become ready?
             ↓
          Scheduler

When should the ready task actually run?
             ↓
           Worker
```

### Worker - `workers.py`

Workers are responsible for actual task execution.

A worker:

1. Finds the highest-priority task
2. Claims it by removing it from the priority queue
3. Reads the task metadata from Redis
4. Changes its status to `RUNNING`
5. Executes the task
6. Stores the result if successful
7. Retries failed tasks when retry attempts remain
8. Marks the task `FAILED` after the retry limit is reached

The current maximum retry count is:

```text
MAX_RETRIES = 3
```

### Task Handlers - `task_handlers.py`

This file contains the actual simulated workloads.

Supported tasks include:

| Task | Simulated Execution Time | Result |
|---|---:|---|
| `send_email` | 2 sec | Email sent |
| `generate_report` | 4 sec | Report generated |
| `resize_image` | 3 sec | Image resized |
| `fail_task` | Fails | Simulates failure |

These are demonstration handlers rather than real external services.

---

## 4. Redis Data Model

Redis acts as the central coordination and state-management layer.

### Task Hash

Each task is stored using a key similar to:

```text
task:<task_id>
```

Example fields:

```text
status   = RUNNING
task     = generate_report
priority = high
retries  = 1
result   = Report generated
```

### Priority Queue

```text
priority_queue
```

This is a Redis sorted set.

Lower score means higher priority:

```text
High    → 1
Normal  → 2
Low     → 3
```

Workers select the lowest-score task first.

### Scheduled Queue

```text
scheduled_tasks
```

This is another Redis sorted set.

The score represents the Unix timestamp at which the task should become ready.

---

## 5. Task Lifecycle

A normal task follows approximately this lifecycle:

```text
PENDING
   ↓
RUNNING
   ↓
COMPLETED
```

A scheduled task follows:

```text
SCHEDULED
   ↓
PENDING
   ↓
RUNNING
   ↓
COMPLETED
```

When execution fails:

```text
RUNNING
   ↓
RETRYING
   ↓
PENDING
   ↓
RUNNING
```

After the retry limit is reached:

```text
RUNNING
   ↓
FAILED
```

---

## 6. Why Do We Need a Scheduler?

A common question is:

> Why not let the worker handle scheduled tasks?

Because scheduling and execution are different responsibilities.

Suppose a task says:

```text
Run this task after 60 seconds.
```

The worker's responsibility is to execute ready tasks, not continuously manage future execution times.

The scheduler acts as a timing component:

```text
Future task
    ↓
scheduled_tasks
    ↓
Scheduler waits/checks
    ↓
Time reached
    ↓
priority_queue
    ↓
Worker executes
```

This separation makes the architecture easier to understand and extend.

---

## 7. Why Do We Need a Broker?

The broker provides a central place through which tasks enter the system.

Without a broker/queue layer, a client would need to communicate directly with a specific worker.

That creates problems when:

- There are multiple workers
- Workers become busy
- Workers restart
- More tasks arrive than workers can process immediately

With Redis acting as shared coordination/storage:

```text
Client
  ↓
Broker
  ↓
Redis Queue
  ↓
Available Worker
```

The producer does not need to know which worker will process the task.

---

## 8. What Happens When Multiple Workers Run?

Multiple workers can consume tasks from the same priority queue.

For example:

```text
             Redis
               │
       ┌───────┼────────┐
       │       │        │
       ▼       ▼        ▼
    Worker 1 Worker 2 Worker 3
```

If five tasks exist and three workers are available:

```text
Task 1 → Worker 1
Task 2 → Worker 2
Task 3 → Worker 3

Task 4 → waits in queue
Task 5 → waits in queue
```

When a worker finishes, it can take another task.

This allows the system to process multiple independent tasks without requiring one worker to do everything sequentially.

### Important implementation note

The current worker uses a `zrange()` followed by `zrem()` to claim a task. The removal acts as the basic claim/check mechanism, but this prototype is not a production-grade atomic distributed queue.

A production implementation could use atomic Redis operations or a dedicated queue/consumer pattern to provide stronger delivery guarantees.

---

## 9. State Management

One of the most important parts of the project is task state.

Redis stores information such as:

```text
PENDING
RUNNING
COMPLETED
RETRYING
FAILED
SCHEDULED
```

This allows the system to answer:

> What is happening with this task?

For example:

```text
Task ID: 1234

Status: RUNNING
Task: generate_report
Priority: high
Retries: 0
```

After completion:

```text
Status: COMPLETED
Result: Report generated
```

State management is important because the queue alone does not provide the full history/context of the task.

---

## 10. Why Redis?

Redis is useful here because it provides several data structures that map naturally to the system:

- **Hash** → task metadata and state
- **List** → basic task queue
- **Sorted Set** → priority queue
- **Sorted Set** → scheduled tasks

For this project, Redis acts as the central shared coordination layer between the broker, scheduler, producers, and workers.

---

## 11. Retry Mechanism

When a worker encounters an exception, it does not immediately mark the task permanently failed.

Instead:

```text
Attempt 1
   ↓
Failure
   ↓
Retry
   ↓
Attempt 2
   ↓
Failure
   ↓
Retry
   ↓
Attempt 3
   ↓
Failure
   ↓
FAILED
```

The retry count is stored with the task in Redis.

Current configuration:

```python
MAX_RETRIES = 3
```

The example task `fail_task` can be used to test this behavior.

---

## 12. Example Tasks

### Successful task

```text
send_email
```

Expected flow:

```text
PENDING
→ RUNNING
→ COMPLETED
```

### Scheduled task

```text
generate_report
delay = 10
```

Expected flow:

```text
SCHEDULED
→ Scheduler detects due task
→ PENDING
→ Worker picks task
→ RUNNING
→ COMPLETED
```

### Failed task

```text
fail_task
```

Expected flow:

```text
RUNNING
→ RETRYING
→ RETRYING
→ FAILED
```

---

## 13. Running the Project

### Prerequisites

Install:

- Python 3.12+
- Redis
- Docker (optional for the current prototype)
- FastAPI dependencies

The project communicates with Redis using:

```text
localhost:6379
```

### Install Python dependencies

Create/activate a virtual environment and install:

```bash
pip install fastapi uvicorn redis pydantic
```

### Start Redis

Make sure Redis is running on:

```text
localhost:6379
```

### Start the FastAPI broker

From the project directory:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### Test the broker

Open:

```text
http://127.0.0.1:8000/
```

You should receive:

```json
{
  "message": "Task Broker is running"
}
```

### Create an API task

Example request:

```http
POST /tasks
Content-Type: application/json
```

```json
{
  "task": "generate_report"
}
```

The response contains a task ID and initial status.

### Run a producer

In another terminal:

```bash
python producers.py
```

### Run the scheduler

In another terminal:

```bash
python scheduler.py
```

### Run a worker

In another terminal:

```bash
python workers.py
```

For multiple workers, run `workers.py` in additional terminals.

### Run the scheduled producer

```bash
python scheduled_producer.py
```

---

## 14. Simple End-to-End Example

Start:

```text
Redis
  ↓
FastAPI Broker
  ↓
Scheduler
  ↓
Worker 1
  ↓
Worker 2 (optional)
```

Then create:

```text
Task: generate_report
Priority: high
```

The system stores the task:

```text
task:<id>
```

and places it in:

```text
priority_queue
```

A worker claims it:

```text
PENDING → RUNNING
```

The handler executes:

```text
Generating report...
```

Then Redis is updated:

```text
COMPLETED
result = Report generated
```

---

## 15. Project Structure

```text
redis-shit/
│
├── main.py                # FastAPI task broker
├── producers.py           # Immediate task producer
├── scheduled_producer.py  # Creates delayed/scheduled tasks
├── scheduler.py           # Moves due tasks into priority queue
├── workers.py             # Task worker and retry logic
├── task_handlers.py       # Simulated task implementations
├── basic.py               # Basic Redis connectivity test
├── Dockerfile             # Basic Docker example
└── README.md
```

> The uploaded project also contains a local `.venv/` directory. It should generally not be committed to GitHub; use `.gitignore` to exclude it.

---

## 16. Architectural Concepts Learned

This project was built to understand several backend and distributed-system concepts:

### Producer

Creates and submits work.

```text
Producer → Queue
```

### Broker

Acts as the entry/coordination layer between clients and workers.

```text
Client → Broker → Queue
```

### Queue

Temporarily stores work until a worker is available.

### Scheduler

Controls **when a future task becomes ready**.

### Worker

Controls **actual task execution**.

### State Manager

Tracks the current state and result of each task.

In this implementation, Redis performs much of this role.

### Retry Mechanism

Allows failed tasks to be attempted again before being permanently marked failed.

### Distributed Processing

Multiple workers can share the same task source and process independent tasks concurrently.

---

## 17. Broker vs Scheduler vs Worker

These components solve different problems:

| Component | Main Responsibility |
|---|---|
| Broker | Accept and coordinate incoming tasks |
| Scheduler | Release scheduled tasks when they become due |
| Queue | Hold tasks waiting for execution |
| Worker | Execute tasks |
| Redis | Store queues, metadata, state, priority, and scheduling information |

A useful mental model is:

```text
Broker  = "Where does work enter?"
Scheduler = "When does future work become ready?"
Queue = "Where does ready work wait?"
Worker = "Who performs the work?"
Redis = "Where do we coordinate and store state?"
```

---

## 18. Does SQLite Handle the Data?

Not in the current implementation.

The current project uses **Redis** for task metadata, queue information, scheduling data, statuses, retries, and results.

SQLite is therefore not required for the current version.

A future version could introduce a persistent relational database such as PostgreSQL for long-term task history, auditing, analytics, or user/account data while Redis remains the fast coordination/queue layer.

---

## 19. Current Limitations

This project is intentionally a prototype. Some production features are not implemented yet.

Examples:

- Authentication and authorization
- Persistent database-backed task history
- Atomic task claiming using a stronger queue-consumer pattern
- Worker heartbeats
- Dead-letter queues
- Job cancellation
- Rate limiting
- Monitoring/dashboard
- Structured logging
- Production-ready Docker Compose deployment
- Failure recovery when a worker crashes after claiming a task
- Exponential backoff for retries

These are natural areas for future improvement.

---

## 20. Future Improvements

Possible next steps:

1. Add Docker Compose for Redis, API, scheduler, and multiple workers
2. Add PostgreSQL for persistent task history
3. Add worker heartbeats and timeout detection
4. Add a dead-letter queue
5. Add exponential retry backoff
6. Add task cancellation
7. Add authentication
8. Add monitoring with metrics and dashboards
9. Add a web-based task management UI
10. Improve task claiming and delivery guarantees

---

## 21. Key Takeaway

The main goal of this project is to understand how a distributed task system can separate:

```text
Task creation
      ↓
Task storage
      ↓
Scheduling
      ↓
Queue management
      ↓
Worker execution
      ↓
State tracking
      ↓
Retry / failure handling
```

The project demonstrates the fundamental architecture behind systems where many tasks need to be processed reliably by one or more workers.

---

## 22. Technologies

- **Python**
- **FastAPI**
- **Redis**
- **Docker**
- **REST API**
- **Distributed task processing**
- **Priority queues**
- **Scheduled jobs**
- **Retry mechanisms**

---

## Author

**Kapil Bhatt**

B.Tech Computer Science & Engineering  
Uttaranchal University — 2027
