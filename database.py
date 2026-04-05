import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Tuple, Set

class Database:
    def __init__(self, db_file="bot_data.db"):
        self.db_file = db_file
        self._lock = asyncio.Lock()
        self._init_tables_sync()

    def _init_tables_sync(self):
        with sqlite3.connect(self.db_file) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS peer_names (
                    peer_id INTEGER,
                    user_id INTEGER,
                    name TEXT,
                    PRIMARY KEY (peer_id, user_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activity (
                    peer_id INTEGER,
                    user_id INTEGER,
                    messages_count INTEGER DEFAULT 0,
                    rolls_count INTEGER DEFAULT 0,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (peer_id, user_id)
                )
            """)
            conn.commit()

    async def _execute(self, query, params=()):
        async with self._lock:
            with sqlite3.connect(self.db_file) as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                return cur

    async def get_name(self, peer_id: int, user_id: int):
        async with self._lock:
            with sqlite3.connect(self.db_file) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM peer_names WHERE peer_id=? AND user_id=?", (peer_id, user_id))
                row = cur.fetchone()
                return row[0] if row else None

    async def set_name(self, peer_id: int, user_id: int, name: str):
        await self._execute(
            "INSERT OR REPLACE INTO peer_names (peer_id, user_id, name) VALUES (?, ?, ?)",
            (peer_id, user_id, name)
        )

    async def get_all_names(self, peer_id: int) -> List[Tuple[int, str]]:
        async with self._lock:
            with sqlite3.connect(self.db_file) as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id, name FROM peer_names WHERE peer_id=?", (peer_id,))
                return cur.fetchall()

    async def update_activity(self, peer_id: int, user_id: int, is_roll: bool = False):
        now = datetime.now().isoformat()
        if is_roll:
            await self._execute(
                """
                INSERT INTO activity (peer_id, user_id, rolls_count, last_activity)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(peer_id, user_id) DO UPDATE SET
                    rolls_count = rolls_count + 1,
                    last_activity = ?
                """, (peer_id, user_id, now, now)
            )
        else:
            await self._execute(
                """
                INSERT INTO activity (peer_id, user_id, messages_count, last_activity)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(peer_id, user_id) DO UPDATE SET
                    messages_count = messages_count + 1,
                    last_activity = ?
                """, (peer_id, user_id, now, now)
            )

    async def get_top(self, peer_id: int, days: int = 0) -> List[Tuple[str, int, int]]:
        async with self._lock:
            with sqlite3.connect(self.db_file) as conn:
                cur = conn.cursor()
                if days > 0:
                    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                    cur.execute(
                        "SELECT user_id, messages_count, rolls_count FROM activity WHERE peer_id=? AND last_activity>=?",
                        (peer_id, cutoff)
                    )
                else:
                    cur.execute("SELECT user_id, messages_count, rolls_count FROM activity WHERE peer_id=?", (peer_id,))
                rows = cur.fetchall()
                result = []
                for uid, msg, roll in rows:
                    name = await self.get_name(peer_id, uid)
                    if not name:
                        name = f"Пользователь {uid}"
                    result.append((name, msg, roll))
                return result

    async def remove_left_users(self, peer_id: int, current_members: Set[int]) -> List[int]:
        async with self._lock:
            with sqlite3.connect(self.db_file) as conn:
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM activity WHERE peer_id=?", (peer_id,))
                db_users = {row[0] for row in cur.fetchall()}
                cur.execute("SELECT user_id FROM peer_names WHERE peer_id=?", (peer_id,))
                db_names = {row[0] for row in cur.fetchall()}
                left = []
                for uid in db_users - current_members:
                    cur.execute("DELETE FROM activity WHERE peer_id=? AND user_id=?", (peer_id, uid))
                    left.append(uid)
                for uid in db_names - current_members:
                    cur.execute("DELETE FROM peer_names WHERE peer_id=? AND user_id=?", (peer_id, uid))
                conn.commit()
                return left

db = Database()
