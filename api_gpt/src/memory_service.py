# memory_service.py
import os, sqlite3
from typing import List, Dict

class MemoryService:
    def __init__(self, db_path: str = "/opt/api/data/memory.db"):
        # создаём папку для базы, если её нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # подключаемся к SQLite (файл создаётся автоматически)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    # ────────── NEW ──────────
    def _create_tables(self):
        with self.conn:
            # история сообщений
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            # текущий модуль (0|2)
            self.conn.execute("""
              CREATE TABLE IF NOT EXISTS session_meta (
                session_id TEXT PRIMARY KEY,
                module     INTEGER
              );
            """)

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        cur = self.conn.cursor()
        # Используем ROWID для порядка даже если таблица была создана без колонки id
        cur.execute(
            "SELECT role, content FROM memory WHERE session_id=? ORDER BY rowid",
            (session_id,)
        )
        rows = cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]

    def append_message(self, session_id: str, role: str, content: str):
        # Обрезаем слишком длинное сообщение
        safe_content = content if len(content) <= 4096 else content[:4096]
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, safe_content)
            )

    def clear_history(self, session_id: str):
        with self.conn:
            self.conn.execute("DELETE FROM memory WHERE session_id=?", (session_id,))
            self.conn.execute("DELETE FROM session_meta WHERE session_id=?", (session_id,))

    # ---------- NEW: модуль ----------
    def get_module(self, session_id) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT module FROM session_meta WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        return row[0] if row else 0                # 0 по-умолчанию

    def set_module(self, session_id, module: int):
        with self.conn:
            self.conn.execute("""
              INSERT INTO session_meta(session_id,module)
              VALUES(?,?)
              ON CONFLICT(session_id) DO UPDATE SET module=excluded.module
            """, (session_id, module))
