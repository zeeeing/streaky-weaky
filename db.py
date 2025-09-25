import os
import sqlite3
from typing import Tuple, List, Dict, Optional

DB_PATH = os.getenv("/", "streak_dev.db")


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Initialize the SQLite database and required tables."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS streaks (
                chat_id INTEGER PRIMARY KEY,
                streak INTEGER NOT NULL DEFAULT 0,
                today_checked TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                chat_id INTEGER NOT NULL,
                tele_id INTEGER NOT NULL,
                lc_user TEXT NOT NULL,
                PRIMARY KEY (chat_id, tele_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_state(chat_id: int) -> Tuple[int, str]:
    """Fetch stored state for a chat. Returns (streak, today_checked)."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT streak, today_checked FROM streaks WHERE chat_id = ?", (chat_id,)
        )
        row = cur.fetchone()
        if row is None:
            return 0, ""
        return int(row[0] or 0), str(row[1] or "")


def set_state(chat_id: int, streak: int, today_checked: str) -> None:
    """Upsert the state for a chat."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO streaks (chat_id, streak, today_checked)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                streak = excluded.streak,
                today_checked = excluded.today_checked
            """,
            (chat_id, streak, today_checked),
        )
        conn.commit()


def get_players(chat_id: int) -> List[Dict[str, str]]:
    """Return a list of players for a chat as dicts: {tele_id, lc_user}."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT tele_id, lc_user FROM players WHERE chat_id = ? ORDER BY tele_id",
            (chat_id,),
        )
        rows = cur.fetchall()
    return [{"tele_id": int(r[0]), "lc_user": str(r[1])} for r in rows]


def upsert_player(chat_id: int, tele_id: int, lc_user: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO players (chat_id, tele_id, lc_user)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, tele_id) DO UPDATE SET
                lc_user = excluded.lc_user
            """,
            (chat_id, tele_id, lc_user),
        )
        conn.commit()


def get_all_chat_ids() -> List[int]:
    """Return chat IDs that have streak or player data."""
    with _connect() as conn:
        cur = conn.execute(
            """
            SELECT chat_id FROM streaks
            UNION
            SELECT DISTINCT chat_id FROM players
            """
        )
        rows = cur.fetchall()
    return [int(row[0]) for row in rows]


def get_group_name(chat_id: int) -> Optional[str]:
    """Return the custom group name if set, else None."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT name FROM groups WHERE chat_id = ?",
            (chat_id,),
        )
        row = cur.fetchone()
        return str(row[0]) if row and row[0] is not None else None


def set_group_name(chat_id: int, name: str) -> None:
    """Upsert the custom group name for a chat."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO groups (chat_id, name)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                name = excluded.name
            """,
            (chat_id, name),
        )
        conn.commit()
