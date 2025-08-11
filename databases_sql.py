
# Simple SQLite helpers. Creates tables if missing and provides helper functions.

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import List, Dict, Any

DB_PATH = Path(__file__).parent / "booking.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    instructor TEXT NOT NULL,
    start_utc TEXT NOT NULL,
    capacity INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    booked_at_utc TEXT NOT NULL,
    FOREIGN KEY(class_id) REFERENCES classes(id)
);
"""


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        cur.executescript(SCHEMA)
        conn.commit()


def insert_class(name: str, instructor: str, start_utc: str, capacity: int) -> int:
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO classes (name, instructor, start_utc, capacity) VALUES (?, ?, ?, ?)",
            (name, instructor, start_utc, capacity),
        )
        conn.commit()
        return cur.lastrowid


def list_classes() -> List[Dict[str, Any]]:
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT * FROM classes ORDER BY start_utc")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_class(class_id: int):
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT * FROM classes WHERE id = ?", (class_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def count_bookings_for_class(class_id: int) -> int:
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM bookings WHERE class_id = ?", (class_id,))
        return cur.fetchone()[0]


def create_booking(class_id: int, name: str, email: str, booked_at_utc: str) -> int:
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        # We'll use a transaction to avoid simple race conditions
        cur.execute("BEGIN")
        cur.execute("SELECT capacity FROM classes WHERE id = ?", (class_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise ValueError("Class not found")
        capacity = row[0]
        cur.execute("SELECT COUNT(*) FROM bookings WHERE class_id = ?", (class_id,))
        booked = cur.fetchone()[0]
        if booked >= capacity:
            conn.rollback()
            raise OverflowError("Class is full")
        cur.execute(
            "INSERT INTO bookings (class_id, name, email, booked_at_utc) VALUES (?, ?, ?, ?)",
            (class_id, name, email, booked_at_utc),
        )
        booking_id = cur.lastrowid
        conn.commit()
        return booking_id


def list_bookings_by_email(email: str) -> List[Dict[str, Any]]:
    conn = get_conn()
    with closing(conn):
        cur = conn.cursor()
        cur.execute(
            "SELECT b.*, c.name as class_name, c.start_utc as class_start_utc FROM bookings b JOIN classes c ON b.class_id = c.id WHERE b.email = ? ORDER BY b.booked_at_utc DESC",
            (email,),
        )
        return [dict(r) for r in cur.fetchall()]
