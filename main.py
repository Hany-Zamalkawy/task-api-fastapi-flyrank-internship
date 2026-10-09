"""Task API — W3 · A2 | Stage 0: SQLite database created"""
import sqlite3
from fastapi import FastAPI

app = FastAPI(title="Task API", version="2.0")
DB_PATH = "tasks.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0)""")
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany("INSERT INTO tasks (title,done) VALUES (?,?)",
                [("Buy groceries",0),("Read FastAPI docs",1),("Push code to GitHub",0)])
        conn.commit()

init_db()

@app.get("/")
def root(): return {"name":"Task API","version":"2.0","storage":"sqlite"}
