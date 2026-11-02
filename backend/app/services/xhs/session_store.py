"""小红书会话的 SQLite 持久化。"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .crypto import CookieCipher

_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "xhs.db"
_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SessionStore:
    def __init__(self, db_path: Optional[Path] = None, key_file: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else _DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cipher = CookieCipher(key_file)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with _LOCK, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS xhs_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_label TEXT NOT NULL DEFAULT 'default',
                    cookie_cipher TEXT NOT NULL,
                    cookie_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_ok_at TEXT,
                    last_probe_at TEXT,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    expires_hint TEXT,
                    user_agent TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_xhs_sessions_status ON xhs_sessions(status, id)"
            )
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row, include_cookie: bool = False) -> Dict[str, Any]:
        data = dict(row)
        if include_cookie:
            data["cookie"] = self.cipher.decrypt(data.get("cookie_cipher", ""))
        data.pop("cookie_cipher", None)
        data["configured"] = True
        return data

    def import_cookie(
        self,
        cookie: str,
        *,
        account_label: str = "default",
        user_agent: str = "",
        status: str = "active",
        note: str = "",
    ) -> int:
        cookie = str(cookie or "").strip()
        if not cookie or "=" not in cookie:
            raise ValueError("Cookie 为空或格式不正确")
        now = _now()
        cipher_text = self.cipher.encrypt(cookie)
        digest = hashlib.sha256(cookie.encode("utf-8")).hexdigest()
        with _LOCK, self._connect() as conn:
            conn.execute(
                "UPDATE xhs_sessions SET status='standby', updated_at=? "
                "WHERE status IN ('active', 'degraded')",
                (now,),
            )
            cursor = conn.execute(
                """
                INSERT INTO xhs_sessions
                    (account_label, cookie_cipher, cookie_hash, status, created_at,
                     updated_at, last_probe_at, user_agent, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_label or "default",
                    cipher_text,
                    digest,
                    status,
                    now,
                    now,
                    now,
                    user_agent or "",
                    str(note or "")[:500],
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_active(self, include_cookie: bool = True) -> Optional[Dict[str, Any]]:
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM xhs_sessions WHERE status != 'disabled' "
                "ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'degraded' THEN 1 "
                "WHEN 'expired' THEN 2 ELSE 3 END, id DESC LIMIT 1"
            ).fetchone()
        return self._row_to_dict(row, include_cookie) if row else None

    def get_latest(self) -> Optional[Dict[str, Any]]:
        with _LOCK, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM xhs_sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def mark_success(self, session_id: int) -> None:
        now = _now()
        with _LOCK, self._connect() as conn:
            conn.execute(
                "UPDATE xhs_sessions SET status='active', fail_count=0, "
                "last_ok_at=?, last_probe_at=?, updated_at=? WHERE id=?",
                (now, now, now, session_id),
            )
            conn.commit()

    def mark_probe(self, session_id: int) -> None:
        with _LOCK, self._connect() as conn:
            conn.execute(
                "UPDATE xhs_sessions SET last_probe_at=?, updated_at=? WHERE id=?",
                (_now(), _now(), session_id),
            )
            conn.commit()

    def mark_failure(self, session_id: int, status: str = "degraded", note: str = "") -> None:
        now = _now()
        with _LOCK, self._connect() as conn:
            conn.execute(
                "UPDATE xhs_sessions SET status=?, fail_count=fail_count+1, "
                "last_probe_at=?, updated_at=?, note=? WHERE id=?",
                (status, now, now, str(note or "")[:500], session_id),
            )
            conn.commit()

    def set_status(self, session_id: int, status: str, note: str = "") -> None:
        with _LOCK, self._connect() as conn:
            conn.execute(
                "UPDATE xhs_sessions SET status=?, note=?, updated_at=? WHERE id=?",
                (status, str(note or "")[:500], _now(), session_id),
            )
            conn.commit()

    def list_sessions(self) -> List[Dict[str, Any]]:
        with _LOCK, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM xhs_sessions ORDER BY id DESC LIMIT 20"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]
