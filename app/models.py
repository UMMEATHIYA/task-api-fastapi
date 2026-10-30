from typing import Annotated

from pydantic import BaseModel, StringConstraints

# Strip whitespace before checking length, so "   " is rejected as empty.
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TaskBase(BaseModel):
    title: NonEmptyStr
    description: str | None = None
    completed: bool = False


class TaskCreate(TaskBase):
    """Request body for POST /tasks."""


class TaskUpdate(TaskBase):
    """Request body for PUT /tasks/{id}. PUT replaces the whole task."""


class Task(TaskBase):
    """A stored task, as returned by the API."""

    id: int
