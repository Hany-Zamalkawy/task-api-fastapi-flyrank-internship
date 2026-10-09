# Task API — W3 · A2 (SQLite)

The same CRUD API from Assignment 1 — identical endpoints, request/response shapes, and status codes — with one change: storage moved from an in-memory list to a SQLite database (`tasks.db`).

Data now survives a server restart.

---

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

API → `http://localhost:8000`  
Swagger UI → `http://localhost:8000/docs`

`tasks.db` is created automatically on first run — no setup needed.

---

## Why SQLite

SQLite is a single file on disk (`tasks.db`). No server to install, no config, zero setup. A stranger who clones this repo and runs the one command above gets a working API with a table and 3 seeded tasks in under a minute. It is the right choice when you want persistence without infrastructure.

---

## What changed from Assignment 1

**One thing changed: the storage layer.**

| Layer | A1 | A2 (this) |
|-------|-----|-----------|
| Routes | in-memory list | ✗ unchanged |
| Schemas / validation | pydantic models | ✗ unchanged |
| Status codes | 200/201/204/400/404 | ✗ unchanged |
| **Storage** | Python list in memory | ✓ SQLite (`tasks.db`) |

The endpoints, request bodies, and responses are identical. Running the A1 curl tests against this version returns the same results — that's the proof that storage is "just an implementation detail."

---

## Endpoints

| Method | Path | What it does | Status codes |
|--------|------|--------------|-------------|
| GET | `/` | API info | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List all tasks | 200 |
| GET | `/tasks/{id}` | Get one task | 200, 404 |
| POST | `/tasks` | Create a task | 201, 400 |
| PUT | `/tasks/{id}` | Update a task | 200, 400, 404 |
| DELETE | `/tasks/{id}` | Delete a task | 204, 404 |
| GET | `/stats` | Task counts (SQL) | 200 |
| POST | `/reset` | Restore seed data | 200 |

---

## Sample curl output

```
$ curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'

HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

```
$ curl -i http://localhost:8000/tasks/99

HTTP/1.1 404 Not Found
content-type: application/json

{"detail":"Task 99 not found"}
```

---

## Persistence proof

1. Start the server: `uvicorn main:app --reload`
2. Create a task: `POST /tasks {"title": "Test persistence"}`
3. Stop the server (Ctrl+C)
4. Start again: `uvicorn main:app --reload`
5. `GET /tasks` — the task is still there

Data lives in `tasks.db` on disk, not in memory.

---

## Stage 4 — SQL queries run by hand (DB Browser)

Open `tasks.db` in [DB Browser for SQLite](https://sqlitebrowser.org/) and run these in the Execute SQL tab:

```sql
-- List every task
SELECT * FROM tasks;

-- Only completed tasks
SELECT * FROM tasks WHERE done = 1;

-- Count tasks
SELECT COUNT(*) FROM tasks;

-- Mark all done
UPDATE tasks SET done = 1;

-- Delete all completed
DELETE FROM tasks WHERE done = 1;
```

After any query that changes data, call `GET /tasks` from the API — it reflects the change immediately. Same file, one source of truth.

---

## Database schema

```sql
CREATE TABLE tasks (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT    NOT NULL,
    done  INTEGER NOT NULL DEFAULT 0
);
```

`done` is stored as `0`/`1` (SQLite has no boolean type) and converted to `true`/`false` in the API response.

---

## All queries use parameterized placeholders

```python
# Safe — value passed separately
conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))

# Never this — string-glued SQL is SQL injection
conn.execute(f"SELECT * FROM tasks WHERE id = {task_id}")
```

---

## Commit log

```
Stage 0: create SQLite database
Stage 1: database read endpoints
Stage 2: insert into database
Stage 3: update and delete with SQL
Stage 4: explored SQLite
Stage 5: database documentation
```
