import sqlite3
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = "subscribers.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'subscribed', -- subscribed | unsubscribed
    token TEXT UNIQUE NOT NULL,
    source TEXT DEFAULT 'form', -- form | manual | upload
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS send_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    template TEXT NOT NULL,
    sent_count INTEGER NOT NULL,
    failed_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def _now():
    return datetime.now(timezone.utc).isoformat()


def upsert_subscriber(email: str, name: str = "", source: str = "form") -> dict:
    """Add a subscriber, or re-activate + update an existing one. Returns the row."""
    email = email.strip().lower()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM subscribers WHERE email = ?", (email,)).fetchone()
        if row:
            conn.execute(
                "UPDATE subscribers SET status = 'subscribed', name = COALESCE(NULLIF(?, ''), name), "
                "updated_at = ? WHERE email = ?",
                (name, _now(), email),
            )
        else:
            token = secrets.token_urlsafe(24)
            conn.execute(
                "INSERT INTO subscribers (email, name, status, token, source, created_at, updated_at) "
                "VALUES (?, ?, 'subscribed', ?, ?, ?, ?)",
                (email, name, token, source, _now(), _now()),
            )
        return dict(conn.execute("SELECT * FROM subscribers WHERE email = ?", (email,)).fetchone())


def bulk_upsert(entries: list[dict], source: str = "upload") -> int:
    """entries: [{'email': ..., 'name': ...}, ...]. Returns count processed."""
    count = 0
    for entry in entries:
        email = (entry.get("email") or "").strip()
        if not email or "@" not in email:
            continue
        upsert_subscriber(email, entry.get("name", ""), source=source)
        count += 1
    return count


def unsubscribe(email: str, token: str) -> bool:
    email = email.strip().lower()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE email = ? AND token = ?", (email, token)
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE subscribers SET status = 'unsubscribed', updated_at = ? WHERE email = ?",
            (_now(), email),
        )
        return True


def get_active_subscribers() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM subscribers WHERE status = 'subscribed' ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def get_subscriber_counts() -> dict:
    with get_conn() as conn:
        active = conn.execute(
            "SELECT COUNT(*) c FROM subscribers WHERE status = 'subscribed'"
        ).fetchone()["c"]
        unsub = conn.execute(
            "SELECT COUNT(*) c FROM subscribers WHERE status = 'unsubscribed'"
        ).fetchone()["c"]
        return {"active": active, "unsubscribed": unsub, "total": active + unsub}


def log_send(subject: str, template: str, sent_count: int, failed_count: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO send_log (subject, template, sent_count, failed_count, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject, template, sent_count, failed_count, _now()),
        )


def get_recent_sends(limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM send_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
