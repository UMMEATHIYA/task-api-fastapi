from fastapi import FastAPI, HTTPException, Response, status

from app.models import Task, TaskCreate, TaskUpdate

app = FastAPI(title="Task API")

# In-memory storage: task id -> Task. Data is lost when the server restarts.
tasks: dict[int, Task] = {}
_next_id = 1


def reset_store() -> None:
    """Clear all tasks and restart ids at 1 (used by tests)."""
    global _next_id
    tasks.clear()
    _next_id = 1


def get_task_or_404(task_id: int) -> Task:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    global _next_id
    task = Task(id=_next_id, **payload.model_dump())
    tasks[task.id] = task
    _next_id += 1
    return task


@app.get("/tasks", response_model=list[Task])
def list_tasks() -> list[Task]:
    return list(tasks.values())


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int) -> Task:
    return get_task_or_404(task_id)


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate) -> Task:
    get_task_or_404(task_id)
    task = Task(id=task_id, **payload.model_dump())
    tasks[task_id] = task
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int) -> Response:
    get_task_or_404(task_id)
    del tasks[task_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
