"""
Task API — W3 · A2
FastAPI · SQLite storage (tasks.db) · Swagger UI at /docs

Storage layer swapped from in-memory to SQLite.
All endpoints, request/response shapes, and status codes
are identical to A1 — only the storage underneath changed.
"""

import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Task API",
    description="A simple CRUD API for managing a to-do list — backed by SQLite.",
    version="2.0",
)

DB_PATH = "tasks.db"

# ── Database setup ────────────────────────────────────────────────────────────

def get_db():
    """Return a connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Stage 0: create the tasks table if missing, then seed 3 example rows
    only when the table is empty. Safe to call on every startup.
    """
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                done  INTEGER NOT NULL DEFAULT 0
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                [
                    ("Buy groceries", 0),
                    ("Read FastAPI docs", 1),
                    ("Push code to GitHub", 0),
                ]
            )
        conn.commit()


# Run once at import time
init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict with done as bool."""
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


# ── Schemas ───────────────────────────────────────────────────────────────────

class TaskIn(BaseModel):
    """Body for POST /tasks"""
    title: str

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()


class TaskUpdate(BaseModel):
    """Body for PUT /tasks/{id} — both fields optional"""
    title: Optional[str] = None
    done: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be empty")
        return v.strip() if v else v


# ── Root & health ─────────────────────────────────────────────────────────────

@app.get("/", summary="API info")
def root():
    return {"name": "Task API", "version": "2.0", "storage": "sqlite", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


# ── Stage 1 — Read ────────────────────────────────────────────────────────────

@app.get("/tasks", summary="List all tasks")
def list_tasks():
    """SELECT * FROM tasks — returns all tasks from the database."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/tasks/{task_id}", summary="Get one task")
def get_task(task_id: int):
    """SELECT * FROM tasks WHERE id = ? — parameterized, never string-glued."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_dict(row)


# ── Stage 2 — Create ──────────────────────────────────────────────────────────

@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(body: TaskIn):
    """INSERT INTO tasks — database assigns the id. Returns 201 + new task."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            (body.title, 0)
        )
        conn.commit()
        new_id = cursor.lastrowid
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (new_id,)
        ).fetchone()
    return row_to_dict(row)


# ── Stage 3 — Update & Delete ─────────────────────────────────────────────────

@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, body: TaskUpdate):
    """UPDATE tasks SET ... WHERE id = ? — returns updated task or 404."""
    if body.title is None and body.done is None:
        raise HTTPException(status_code=400, detail="Body must include title or done")

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        new_title = body.title if body.title is not None else row["title"]
        new_done  = int(body.done) if body.done is not None else row["done"]

        conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (new_title, new_done, task_id)
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return row_to_dict(updated)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """DELETE FROM tasks WHERE id = ? — returns 204 or 404."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()


# ── Bonus — Stats & Reset ─────────────────────────────────────────────────────

@app.get("/stats", summary="Task statistics")
def stats():
    """SELECT COUNT(*) — computed in SQL, not in Python."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done  = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    return {"total": total, "done": done, "open": total - done}


@app.post("/reset", summary="Reset to seed data")
def reset():
    """Clears all tasks and re-seeds the 3 examples."""
    with get_db() as conn:
        conn.execute("DELETE FROM tasks")
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy groceries", 0),
                ("Read FastAPI docs", 1),
                ("Push code to GitHub", 0),
            ]
        )
        conn.commit()
    return {"message": "Reset to seed data"}
