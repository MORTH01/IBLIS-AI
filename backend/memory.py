import sqlite3
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/memory.db")
CHROMA_PATH = Path("data/chroma")


class MemoryManager:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._init_chroma()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def _init_chroma(self):
        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            self._collection = self._chroma_client.get_or_create_collection(
                name="personal_memory",
                metadata={"hnsw:space": "cosine"}
            )
            self._use_chroma = True
        except Exception:
            print("ChromaDB not available. Using keyword search fallback.")
            self._use_chroma = False

    def store_conversation(self, session_id: str, user_msg: str, ai_msg: str):
        now = datetime.now().isoformat()
        title = user_msg[:60].strip()
        if len(user_msg) > 60:
            title += "..."

        with self._conn() as conn:
            existing = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (now, session_id)
                )
            else:
                conn.execute(
                    "INSERT INTO sessions VALUES (?, ?, ?, ?)",
                    (session_id, title, now, now)
                )
            for role, content in [("user", user_msg), ("assistant", ai_msg)]:
                conn.execute(
                    "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), session_id, role, content, now)
                )

        if self._use_chroma:
            doc = f"User: {user_msg}\nAssistant: {ai_msg}"
            try:
                self._collection.add(
                    documents=[doc],
                    ids=[str(uuid.uuid4())],
                    metadatas=[{"session_id": session_id, "timestamp": now}]
                )
            except Exception as e:
                print(f"ChromaDB store error: {e}")

    def search(self, query: str, n_results: int = 8) -> list:
        if self._use_chroma:
            try:
                count = self._collection.count()
                if count == 0:
                    return []
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(n_results, count)
                )
                return [d[:300] for d in results.get("documents", [[]])[0] if d]
            except Exception as e:
                print(f"ChromaDB query error: {e}")

        with self._conn() as conn:
            words = query.lower().split()[:3]
            if not words:
                return []
            like_clauses = " OR ".join(["LOWER(content) LIKE ?" for _ in words])
            params = [f"%{w}%" for w in words]
            rows = conn.execute(
                f"SELECT content FROM conversations WHERE {like_clauses} ORDER BY timestamp DESC LIMIT {n_results}",
                params
            ).fetchall()
            return [r[0][:300] for r in rows]

    def get_session_history(self, session_id: str, limit: int = 20) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT role, content FROM conversations
                   WHERE session_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (session_id, limit)
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def get_sessions(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
        result = []
        for r in rows:
            with self._conn() as conn2:
                count = conn2.execute(
                    "SELECT COUNT(*) FROM conversations WHERE session_id = ?", (r[0],)
                ).fetchone()[0]
            if count > 0:
                result.append({
                    "session_id": r[0], "title": r[1],
                    "created_at": r[2], "updated_at": r[3],
                    "message_count": count
                })
        return result

    def get_recent(self, limit: int = 20) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, role, content, timestamp FROM conversations ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"session_id": r[0], "role": r[1], "content": r[2][:150], "timestamp": r[3]} for r in rows]

    def delete_session(self, session_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def clear_all(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM conversations")
            conn.execute("DELETE FROM sessions")