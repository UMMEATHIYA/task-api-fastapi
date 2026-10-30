# Task API (FastAPI practice)

A small REST API for managing tasks, built with **FastAPI** and **Pydantic**, with **pytest** tests.
Tasks are stored in memory, so they disappear when the server restarts.

## Project structure

```
01-rest-api-basics/
├── requirements.txt       # pinned dependencies
├── app/
│   ├── models.py          # Pydantic models (validation)
│   └── main.py            # FastAPI app, in-memory store, endpoints
├── tests/
│   └── test_tasks.py      # pytest tests for every endpoint
└── INTERVIEW_QA.md        # interview questions and answers about this project
```

## Setup (Windows, PowerShell)

```powershell
python -m venv .venv            # only if .venv doesn't exist yet
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the server

```powershell
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for interactive Swagger UI, where you can try every endpoint.

## Run the tests

```powershell
python -m pytest -v
```

## Task fields

| Field | Type | Required | Default |
|---|---|---|---|
| `id` | int | set by the server | auto-increment |
| `title` | string | yes (can't be empty or only spaces) | - |
| `description` | string or null | no | `null` |
| `completed` | bool | no | `false` |

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| POST | `/tasks` | 201 Created | 422 invalid body |
| GET | `/tasks` | 200 OK | - |
| GET | `/tasks/{id}` | 200 OK | 404 not found, 422 non-integer id |
| PUT | `/tasks/{id}` | 200 OK | 404 not found, 422 invalid body |
| DELETE | `/tasks/{id}` | 204 No Content | 404 not found |

PUT is a **full replacement**: any field you leave out goes back to its default.

## Diagrams (quick revision)

### 1. Big picture: how a request flows

```mermaid
flowchart LR
    C["Client<br/>browser / curl / Swagger UI"] -->|"HTTP request + JSON"| U["Uvicorn<br/>ASGI web server"]
    U --> F["FastAPI app<br/>app/main.py"]
    F --> R{"Router<br/>match method + path"}
    R --> V["Pydantic validation<br/>app/models.py<br/>path id is int? body valid?"]
    V -->|invalid| E422["422<br/>Unprocessable Content"]
    V -->|valid| H["Route handler<br/>create / list / get / update / delete"]
    H --> G["get_task_or_404()<br/>GET one, PUT, DELETE"]
    G -->|id missing| E404["404<br/>Not Found"]
    G -->|found| S[("In-memory store<br/>tasks: dict[int, Task]<br/>_next_id counter")]
    H -->|"POST and GET all"| S
    S --> OK["Success<br/>201 POST / 200 GET, PUT / 204 DELETE"]
    OK -->|"JSON response"| C
    E422 --> C
    E404 --> C
```

### 2. Which status code will I get?

```mermaid
flowchart TD
    A["Request arrives"] --> B{"Route exists?"}
    B -->|no| X0["404 / 405<br/>(FastAPI built-in)"]
    B -->|yes| C{"Path id is an int?<br/>e.g. /tasks/abc"}
    C -->|no| X1["422"]
    C -->|yes| D{"Body valid?<br/>POST and PUT only"}
    D -->|"no: missing / empty title,<br/>wrong type"| X2["422"]
    D -->|yes| E{"Task exists?<br/>GET one, PUT, DELETE"}
    E -->|no| X3["404 Task not found"]
    E -->|"yes, or no id needed"| F{"Method?"}
    F -->|POST| S1["201 Created + task"]
    F -->|"GET / PUT"| S2["200 OK + task(s)"]
    F -->|DELETE| S3["204 No Content, empty body"]
```

> Validation runs **before** the handler, so `PUT /tasks/999` with an empty title returns **422**, not 404.

### 3. POST /tasks step by step

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant F as FastAPI
    participant P as Pydantic (TaskCreate)
    participant H as create_task()
    participant S as tasks dict
    C->>F: POST /tasks with JSON body
    F->>P: validate body
    alt invalid (missing / empty title, wrong type)
        P-->>F: validation error
        F-->>C: 422 + error details
    else valid
        P-->>F: TaskCreate object
        F->>H: create_task(payload)
        H->>S: tasks[_next_id] = Task(id, ...fields)
        H->>H: _next_id += 1
        H-->>F: Task
        F-->>C: 201 + Task JSON
    end
```

### 4. GET one / PUT / DELETE: the shared 404 check

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant H as Handler
    participant G as get_task_or_404()
    participant S as tasks dict
    C->>H: GET / PUT / DELETE /tasks/ID
    H->>G: get_task_or_404(ID)
    G->>S: tasks.get(ID)
    alt not found (None)
        G-->>C: raise HTTPException, 404 "Task not found"
    else found
        S-->>G: Task
        G-->>H: Task
        H->>S: GET reads it / PUT replaces it / DELETE removes it
        H-->>C: 200 Task (GET, PUT) or 204 empty (DELETE)
    end
```

### 5. Pydantic models

```mermaid
classDiagram
    direction LR
    class BaseModel {
        Pydantic base class
        validates on creation
    }
    class TaskBase {
        +str title  required, spaces stripped, min length 1
        +str description  optional, default None
        +bool completed  default False
    }
    class TaskCreate {
        POST body
    }
    class TaskUpdate {
        PUT body, full replace
    }
    class Task {
        +int id  set by server only
        response model + stored object
    }
    BaseModel <|-- TaskBase
    TaskBase <|-- TaskCreate
    TaskBase <|-- TaskUpdate
    TaskBase <|-- Task
```

> Clients send `TaskCreate`/`TaskUpdate` (no `id`). The server stores and returns `Task` (with `id`).

### 6. How the tests run

```mermaid
flowchart LR
    P["pytest<br/>finds test_*.py"] --> FX["autouse fixture<br/>clean_store()<br/>calls reset_store()"]
    FX -->|"empty store, ids start at 1"| T["test_* function"]
    T -->|"arrange: create_task() helper"| TC["TestClient(app)<br/>in memory, no real server"]
    TC --> APP["FastAPI app"]
    APP --> RESP["Response"]
    RESP --> AS["assert status code + JSON"]
    AS -->|"PUT / DELETE tests"| V["follow-up GET<br/>verify state really changed"]
```

### 7. Why in-memory storage doesn't scale (and the fix)

```mermaid
flowchart LR
    subgraph NOW["Now: in-memory, broken with many servers"]
        LB1["Load balancer"] --> A1["Server 1<br/>own tasks dict<br/>ids 1, 2, 3"]
        LB1 --> A2["Server 2<br/>own tasks dict<br/>ids 1, 2, 3"]
    end
    subgraph FIX["Fix: one shared database"]
        LB2["Load balancer"] --> B1["Server 1"]
        LB2 --> B2["Server 2"]
        B1 --> DB[("Database<br/>single source of truth<br/>generates ids")]
        B2 --> DB
    end
```

> Created on Server 1, then read from Server 2, gives a 404. Ids also clash, because each server counts from 1.

### Example

```powershell
curl.exe -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{\"title\": \"Buy milk\"}'
```
Response (201):
```json
{"title": "Buy milk", "description": null, "completed": false, "id": 1}
```

## Design notes

- **In-memory dict** (`id -> Task`) for O(1) lookup by id. An id counter means ids are never reused after a delete.
- **`get_task_or_404` helper** keeps the 404 logic in one place.
- **Separate request and response models** (`TaskCreate`/`TaskUpdate` vs `Task`), so clients can't set the `id`.
- **Tests are isolated:** an `autouse` fixture resets the store before every test.

## Limitations (fine for practice)

- Data is lost on restart, and isn't shared across multiple server processes.
- No locking, so it isn't safe under heavy concurrent writes.
- No PATCH (partial update), pagination, or authentication.
