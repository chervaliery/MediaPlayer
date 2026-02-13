"""SQLite store for public share links."""
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _utcnow() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init(db_path: str) -> None:
    """Create DB directory if needed and create shares table if not exists."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shares (
            token TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            revoked_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_by_token(db_path: str, token: str) -> dict | None:
    """Return share row as dict or None if not found."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT token, file_path, created_at, expires_at, revoked_at FROM shares WHERE token = ?",
        (token,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_active_by_file_path(db_path: str, file_path: str) -> dict | None:
    """Return active (non-revoked, non-expired) share for file_path or None."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT token, file_path, created_at, expires_at, revoked_at
        FROM shares
        WHERE file_path = ? AND revoked_at IS NULL
          AND (expires_at IS NULL OR expires_at > datetime('now'))
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (file_path,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def create_share(db_path: str, file_path: str, expires_at_seconds: int | None) -> str:
    """Insert a new share; return token. Token is urlsafe base64."""
    token = secrets.token_urlsafe(32)
    created = _utcnow()
    if expires_at_seconds is None:
        expires_at = None
    else:
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute(
            "SELECT datetime('now', ?)",
            (f"+{expires_at_seconds} seconds",),
        )
        expires_at = cur.fetchone()[0]
        conn.close()
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO shares (token, file_path, created_at, expires_at, revoked_at) VALUES (?, ?, ?, ?, NULL)",
        (token, file_path, created, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def revoke(db_path: str, token: str) -> bool:
    """Set revoked_at to now. Return True if a row was updated."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.execute(
        "UPDATE shares SET revoked_at = datetime('now') WHERE token = ? AND revoked_at IS NULL",
        (token,),
    )
    updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def is_share_active(row: dict) -> bool:
    """Return True if share is not revoked and not expired."""
    if row.get("revoked_at"):
        return False
    exp = row.get("expires_at")
    if exp is None:
        return True
    try:
        # SQLite datetime format: YYYY-MM-DD HH:MM:SS (UTC)
        exp_dt = datetime.fromisoformat(exp.replace("Z", ""))
        return exp_dt > datetime.utcnow()
    except (ValueError, TypeError):
        return False
