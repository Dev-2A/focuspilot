import sqlite3
from pathlib import Path
from datetime import datetime, date
from typing import List, Tuple, Optional

def today_str() -> str:
    return date.today().isoformat()

def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()

def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        title TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        start_ts TEXT NOT NULL,
        end_ts TEXT NOT NULL,
        minutes INTEGER NOT NULL
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS distractions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        ts TEXT NOT NULL,
        note TEXT NOT NULL
    );
    """)
    
    conn.commit()

def upsert_goals(conn: sqlite3.Connection, date_s: str, titles: List[str]) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM goals WHERE date = ?", (date_s,))
    for t in titles[:3]:
        t = (t or "").strip()
        if not t:
            continue
        cur.execute("INSERT INTO goals(date, title, done) VALUES(?,?,0)", (date_s, t))
    conn.commit()

def list_goals(conn: sqlite3.Connection, date_s: str):
    cur = conn.cursor()
    rows = cur.execute("SELECT id, date, title, done FROM goals WHERE date=? ORDER BY id", (date_s,)).fetchall()
    return [dict(r) for r in rows]

def toggle_goal(conn: sqlite3.Connection, goal_id: int) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE goals SET done = CASE done WHEN 0 THEN 1 ELSE 0 END WHERE id=?", (goal_id,))
    conn.commit()

def add_distraction(conn: sqlite3.Connection, date_s: str, note: str) -> None:
    note = (note or "").strip()
    if not note:
        return
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO distractions(date, ts, note) VALUES(?,?,?)",
        (date_s, now_iso(), note[:200])
    )
    conn.commit()

def list_distractions(conn: sqlite3.Connection, date_s: str):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, date, ts, note FROM distractions WHERE date=? ORDER BY id DESC",
        (date_s,)
    ).fetchall()
    return [dict(r) for r in rows]

def add_session(conn: sqlite3.Connection, date_s: str, start_ts: str, end_ts: str, minutes: int) -> None:
    minutes = int(minutes)
    if minutes <= 0:
        return
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions(date, start_ts, end_ts, minutes) VALUES(?,?,?,?)",
        (date_s, start_ts, end_ts, minutes)
    )
    conn.commit()

def list_sessions(conn: sqlite3.Connection, date_s: str):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, date, start_ts, end_ts, minutes FROM sessions WHERE date=? ORDER BY id DESC",
        (date_s,)
    ).fetchall()
    return [dict(r) for r in rows]

def report_summary(conn: sqlite3.Connection, date_s: str):
    cur = conn.cursor()
    
    total_minutes = cur.execute(
        "SELECT COALESCE(SUM(minutes), 0) AS m FROM sessions WHERE date=?",
        (date_s,)
    ).fetchone()["m"]
    
    session_count = cur.execute(
        "SELECT COUNT(*) AS c FROM sessions WHERE date=?",
        (date_s,)
    ).fetchone()["c"]
    
    distraction_count = cur.execute(
        "SELECT COUNT(*) AS c FROM distractions WHERE date=?",
        (date_s,)
    ).fetchone()["c"]
    
    top_distractions = cur.execute(
        """
        SELECT note, COUNT(*) AS c
        FROM distractions
        WHERE date=?
        GROUP BY note
        ORDER BY c DESC, note ASC
        LIMIT 5
        """,
        (date_s,)
    ).fetchall()
    
    goals_done = cur.execute(
        "SELECT COALESCE(SUM(done), 0) AS d, COUNT(*) AS t FROM goals WHERE date=?",
        (date_s,)
    ).fetchone()
    
    return {
        "date": date_s,
        "total_minutes": int(total_minutes),
        "session_count": int(session_count),
        "distractioni_count": int(distraction_count),
        "top distractions": [dict(r) for r in top_distractions],
        "goals_done": int(goals_done["d"]),
        "goals_total": int(goals_done["t"]),
    }