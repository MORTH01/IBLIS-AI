"""
Profile Manager
---------------
Stores and manages the user's persistent profile:
  - Personal info (name, role, timezone, etc.)
  - Projects & work context
  - Preferences
  - Task list
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path


DB_PATH = Path("data/profile.db")

DEFAULT_PROFILE = {
    "name": "",
    "role": "",
    "timezone": "",
    "work_style": "",
    "current_projects": [],
    "skills": [],
    "goals": [],
    "preferences": {
        "communication_style": "direct",
        "response_length": "concise",
        "areas_of_interest": []
    },
    "about": "",
    "notes": ""
}


class ProfileManager:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._conn() as conn:
            # Profile table (single JSON blob)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    priority TEXT DEFAULT 'medium',
                    due TEXT,
                    notes TEXT,
                    done INTEGER DEFAULT 0,
                    created_at TEXT,
                    completed_at TEXT
                )
            """)
            # Seed default profile if empty
            existing = conn.execute(
                "SELECT value FROM profile WHERE key = 'main'"
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO profile VALUES ('main', ?, ?)",
                    (json.dumps(DEFAULT_PROFILE), datetime.now().isoformat())
                )

    # ── Profile ───────────────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM profile WHERE key = 'main'"
            ).fetchone()
        return json.loads(row[0]) if row else DEFAULT_PROFILE.copy()

    def update_profile(self, updates: dict):
        current = self.get_profile()
        # Deep merge
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(current.get(k), dict):
                current[k].update(v)
            elif isinstance(v, list) and isinstance(current.get(k), list):
                # Merge lists (unique items)
                existing = current[k]
                for item in v:
                    if item not in existing:
                        existing.append(item)
                current[k] = existing
            else:
                current[k] = v

        with self._conn() as conn:
            conn.execute(
                "UPDATE profile SET value = ?, updated_at = ? WHERE key = 'main'",
                (json.dumps(current), datetime.now().isoformat())
            )

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def get_tasks(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, priority, due, notes, done, created_at FROM tasks ORDER BY done ASC, priority DESC, created_at DESC"
            ).fetchall()
        return [
            {
                "id": r[0], "title": r[1], "priority": r[2],
                "due": r[3], "notes": r[4], "done": bool(r[5]),
                "created_at": r[6]
            }
            for r in rows
        ]

    def add_task(self, task: dict) -> dict:
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO tasks (id, title, priority, due, notes, done, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
                (task_id, task["title"], task.get("priority", "medium"),
                 task.get("due"), task.get("notes"), now)
            )
        return {**task, "id": task_id, "done": False, "created_at": now}

    def complete_task(self, task_id: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE tasks SET done = 1, completed_at = ? WHERE id = ?",
                (datetime.now().isoformat(), task_id)
            )

    def delete_task(self, task_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def update_task(self, task_id: str, updates: dict):
        allowed = ["title", "priority", "due", "notes"]
        sets = ", ".join(f"{k} = ?" for k in updates if k in allowed)
        vals = [v for k, v in updates.items() if k in allowed]
        if sets:
            with self._conn() as conn:
                conn.execute(
                    f"UPDATE tasks SET {sets} WHERE id = ?",
                    vals + [task_id]
                )
