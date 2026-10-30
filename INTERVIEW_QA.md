# Interview Questions and Answers: Task API

Simple answers you can say out loud. The **first line** of each answer is the short version. The rest is what to add if they ask for more.

---

## HTTP and REST

### 1. Why does POST return 201 instead of 200?
"201 means **Created**. It tells the client something new was made, not just that the request worked."

200 just means OK, so 201 is more specific for a create.

### 2. What's the difference between 404 and 422?
"404 means the thing **doesn't exist**. 422 means the request has **bad data**."

- 404: `GET /tasks/999` when there's no task 999.
- 422: creating a task with an empty title, or `GET /tasks/abc` where the id isn't a number.

Easy way to remember: **404 = not found, 422 = wrong input.**

### 3. What's the difference between 400 and 422?
"400 means the request itself is broken, like JSON that can't be parsed. 422 means the JSON parsed fine but the values broke the rules."

FastAPI uses 422 for validation errors by default.

### 4. What does 202 mean? Did you use it?
"202 means **Accepted**: the server got the request but hasn't finished the work yet, like a background job. I didn't use it because every action here finishes right away."

### 5. Why does DELETE return 204?
"204 means **No Content**: it worked, and there's nothing to send back."

I return an explicit `Response(status_code=204)` so the body is truly empty. If the function returned `None`, FastAPI might send the JSON text `null`.

### 6. What's the difference between PUT and PATCH?
"PUT **replaces the whole thing**. PATCH **changes only what I send**."

- PUT: if I leave out a field, it goes back to its default.
- PATCH: if I send just `completed: true`, everything else stays the same.

Example: rewriting a whole form (PUT) versus correcting one box on it (PATCH).

### 7. Which of your endpoints are idempotent?
"GET, PUT and DELETE are idempotent. Doing them twice leaves the server in the same state as doing them once. POST isn't, because each call creates a new task."

A second DELETE returns 404, but the state is the same: the task is gone.

---

## Pydantic and validation

### 8. What is Pydantic and why use it?
"Pydantic validates and converts data using Python type hints. I describe the data as a class, and bad input is rejected before it reaches my code."

It also gives you defaults, clear error messages, type conversion (`"5"` → `5`), and JSON serialization. FastAPI uses the same models to build the `/docs` page.

### 9. Why a separate `TaskCreate` model instead of just `Task`?
"Because the user shouldn't choose the id; the server does."

`TaskCreate` is what the client is allowed to send. `Task` is what the server sends back, with the id. This keeps clients from setting fields they shouldn't control.

### 10. How do you stop a title that's just spaces?
"I use `StringConstraints(strip_whitespace=True, min_length=1)`, so whitespace is stripped first and then the length is checked."

Only `min_length=1` would let `"   "` through.

### 11. How does FastAPI know to validate the request body?
"From the type hint. When a parameter is a Pydantic model, like `payload: TaskCreate`, FastAPI reads the JSON body and validates it. If it's invalid, the client gets a 422 and my function never runs."

Path parameters work the same way: `task_id: int` makes `/tasks/abc` return 422.

---

## Code design

### 12. Why store tasks in a dict instead of a list?
"A dict gives O(1) lookup by id. With a list I'd have to search through every task to find one."

### 13. Why use a counter for ids instead of `len(tasks) + 1`?
"So ids are never reused. If I delete task 2 out of 3, `len + 1` would give 3 again, which clashes with an existing task."

### 14. Why the `get_task_or_404` helper?
"GET, PUT and DELETE all need 'find the task or return 404'. The helper keeps that logic in one place, so there's no copy-paste and only one spot to change."

### 15. Why do you need `global _next_id`?
"Because the function reassigns `_next_id`. Without `global`, Python would treat it as a new local variable and raise an error."

`tasks.clear()` doesn't need `global` because it changes the existing dict instead of reassigning it.

### 16. What does `**payload.model_dump()` do?
"`model_dump()` turns the model into a dict, and `**` unpacks that dict into keyword arguments. So `Task(id=1, **payload.model_dump())` builds a Task from the input plus the id."

---

## Testing

### 17. What is a pytest fixture?
"Reusable setup code that pytest runs for you before a test."

A fixture can provide a value (the test asks for it by parameter name) or do setup and cleanup using `yield`. Scope controls how often it runs: per test, per module, or per session.

### 18. What does `autouse=True` do, and why does it matter?
"It makes the fixture run automatically before every test. Here it clears the task list, so every test starts fresh."

Without it, one test's data could leak into another and cause random failures that depend on test order.

### 19. What is `TestClient`?
"It calls the FastAPI app directly in memory, with no real server or network. That makes the tests fast and reliable."

It's built on httpx, which is why httpx is in `requirements.txt`.

### 20. How do you know an update or delete really worked?
"I don't just check the response. I make a second GET to confirm the stored state changed. After DELETE, a GET should return 404."

### 21. Why `@pytest.mark.parametrize`?
"It runs the same test with different inputs. I used it to check that both `""` and `"   "` are rejected, without writing two tests."

---

## Scaling and production

### 22. If this ran on three servers behind a load balancer, what would break?
"Each server would have its own separate memory."

If I create a task on server 1 and my next request goes to server 2, I get a 404, because server 2 never saw that task. The ids would also clash, since each server counts from 1. The fix is one shared database that all servers use, with the database creating the ids.

### 23. Is the in-memory store safe with many requests at once?
"Not fully. Two requests could read the same `_next_id` before either one increments it, and both tasks would get the same id. A database handles this, or a lock would fix it for practice."

### 24. What would you add to make this production-ready?
"A real database, plus PATCH for partial updates, pagination for `GET /tasks`, authentication, logging, and Docker for deployment."
