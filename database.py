import os, sqlite3
from pathlib import Path
DB = Path(os.getenv("DATA_DIR", "/data")) / "bot.sqlite3"

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB)

def init_db():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        c.execute("CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")

def add_user(uid):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (uid,))
        c.execute("INSERT INTO jobs DEFAULT VALUES")

def stats():
    with connect() as c:
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        jobs = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    return users, jobs
