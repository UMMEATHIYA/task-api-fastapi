import pytest
from fastapi.testclient import TestClient

from app.main import app, reset_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    """Start every test with an empty store so tests don't affect each other."""
    reset_store()


def create_task(**overrides) -> dict:
    payload = {"title": "Buy milk", **overrides}
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


# ---------- POST /tasks ----------

def test_create_task_with_all_fields():
    response = client.post(
        "/tasks",
        json={"title": "Write tests", "description": "Cover every endpoint", "completed": True},
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "title": "Write tests",
        "description": "Cover every endpoint",
        "completed": True,
    }


def test_create_task_uses_defaults():
    task = create_task()
    assert task["description"] is None
    assert task["completed"] is False


def test_create_task_assigns_increasing_ids():
    assert create_task()["id"] == 1
    assert create_task()["id"] == 2


def test_create_task_missing_title_returns_422():
    response = client.post("/tasks", json={"description": "no title"})
    assert response.status_code == 422


@pytest.mark.parametrize("title", ["", "   "])
def test_create_task_empty_title_returns_422(title):
    response = client.post("/tasks", json={"title": title})
    assert response.status_code == 422


def test_create_task_invalid_completed_type_returns_422():
    response = client.post("/tasks", json={"title": "x", "completed": "abc"})
    assert response.status_code == 422


# ---------- GET /tasks ----------

def test_list_tasks_empty():
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_returns_all_tasks():
    first = create_task(title="First")
    second = create_task(title="Second")
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == [first, second]


# ---------- GET /tasks/{id} ----------

def test_get_task_found():
    task = create_task()
    response = client.get(f"/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json() == task


def test_get_task_not_found_returns_404():
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_get_task_non_integer_id_returns_422():
    response = client.get("/tasks/abc")
    assert response.status_code == 422


# ---------- PUT /tasks/{id} ----------

def test_update_task():
    task = create_task()
    updated = {"title": "Buy oat milk", "description": "2 cartons", "completed": True}
    response = client.put(f"/tasks/{task['id']}", json=updated)
    assert response.status_code == 200
    assert response.json() == {"id": task["id"], **updated}
    # The change is persisted.
    assert client.get(f"/tasks/{task['id']}").json() == {"id": task["id"], **updated}


def test_update_task_not_found_returns_404():
    response = client.put("/tasks/999", json={"title": "Nope"})
    assert response.status_code == 404


def test_update_task_empty_title_returns_422():
    task = create_task()
    response = client.put(f"/tasks/{task['id']}", json={"title": ""})
    assert response.status_code == 422


# ---------- DELETE /tasks/{id} ----------

def test_delete_task():
    task = create_task()
    response = client.delete(f"/tasks/{task['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_delete_task_not_found_returns_404():
    response = client.delete("/tasks/999")
    assert response.status_code == 404
