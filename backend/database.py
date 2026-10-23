"""
database.py – SQLite connection pool & helpers for TorobGard.
Uses a single on-disk database (torob.db) with FTS5 for product search.
"""

import sqlite3
import os
import math
import threading
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "torob.db")

_local = threading.local()


def _haversine_m_udf(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters – exposed to SQL as HAVERSINE_M.

    Registered as a deterministic UDF because SQLite's optional math
    functions (sin/cos/asin) are not guaranteed to be compiled in.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000.0 * 2 * math.asin(math.sqrt(a))


def get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA cache_size=-64000;")  # 64 MB cache
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.create_function("HAVERSINE_M", 4, _haversine_m_udf, deterministic=True)
        _local.conn = conn
    return conn


@contextmanager
def db_cursor():
    """Yield a cursor, auto-commit on success."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def dict_from_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return list of dicts."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        return [dict_from_row(r) for r in cur.fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT and return first row as dict or None."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict_from_row(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """Execute an INSERT/UPDATE/DELETE and return rowcount."""
    with db_cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def db_exists() -> bool:
    """Check if the database file exists and has tables."""
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        r = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='shops'"
        ).fetchone()
        conn.close()
        return r[0] > 0
    except Exception:
        return False
