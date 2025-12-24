from __future__ import annotations

import os
import sqlite3
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Tuple, Optional

from flask import Flask, render_template, request, redirect, url_for

APP_NAME = os.getenv("APP_NAME", "FocusPilot")
DB_PATH = os.getenv("DB_PATH", "focuspilot.db")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8001"))
DEBUG = os.getenv("DEBUG", "1") == "1"

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static",
    static_url_path="/static",
)

# -----------------------------
# DB helpers
# -----------------------------
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def today_str() -> str:
    return date.today().isoformat()

def parse_date(s: Optional[str], fallback: str) -> str:
    if not s:
        return fallback
    try:
        # strict validate
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        return fallback

def iso_now_local() -> str:
    return datetime.now().replace(microsecond=0).isoformat()

def ensure_schema() -> None:
    """
    v0.2: goals 테이블에 goal_date/slot 개념 추가.
    기존 v0.1 goals 구조가 달라도, 가능한 한 안전하게 마이그레이션 시도.
    """
    with get_db() as conn:
        cur = conn.cursor()

        # sessions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          start_ts TEXT NOT NULL,
          end_ts   TEXT NOT NULL,
          minutes  INTEGER NOT NULL
        )
        """)

        # distractions
        cur.execute("""
        CREATE TABLE IF NOT EXISTS distractions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts   TEXT NOT NULL,
          note TEXT NOT NULL
        )
        """)

        # goals (v0.2 schema)
        # goal_date + slot(1..3)로 "오늘의 3개 목표"를 날짜별 관리
        cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          goal_date TEXT NOT NULL,
          slot INTEGER NOT NULL,
          title TEXT NOT NULL,
          done INTEGER NOT NULL DEFAULT 0,
          UNIQUE(goal_date, slot)
        )
        """)

        # --- best-effort migration for older goals table without goal_date/slot ---
        # 만약 기존 goals 테이블이 "id,title,done" 같은 구조였으면, 이미 CREATE가 지나서 여기서 감지 불가.
        # 하지만 v0.1에서 goals 테이블이 다른 이름이었을 수도 있고,
        # 여기서는 'goals'가 이미 존재할 때 컬럼 누락을 점검한다.
        cur.execute("PRAGMA table_info(goals)")
        cols = [r["name"] for r in cur.fetchall()]
        needed = {"goal_date", "slot", "title", "done"}
        if not needed.issubset(set(cols)):
            # 희귀 케이스: goals가 존재하지만 스키마가 다름 → 새 테이블로 교체
            # 기존 데이터 최대한 살려서 오늘 날짜 slot=1..3로 옮김
            cur.execute("ALTER TABLE goals RENAME TO goals_old")

            cur.execute("""
            CREATE TABLE goals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              goal_date TEXT NOT NULL,
              slot INTEGER NOT NULL,
              title TEXT NOT NULL,
              done INTEGER NOT NULL DEFAULT 0,
              UNIQUE(goal_date, slot)
            )
            """)

            # old에서 title/done 비슷한 컬럼이 있으면 옮김
            cur.execute("PRAGMA table_info(goals_old)")
            old_cols = [r["name"] for r in cur.fetchall()]
            has_title = "title" in old_cols
            has_done = "done" in old_cols

            if has_title:
                rows = cur.execute("SELECT * FROM goals_old ORDER BY id ASC LIMIT 3").fetchall()
                d = (date.today() - timedelta(days=1)).isoformat()
                for i, row in enumerate(rows, start=1):
                    title = row["title"]
                    done = int(row["done"]) if has_done else 0
                    cur.execute(
                        "INSERT OR REPLACE INTO goals(goal_date, slot, title, done) VALUES (?, ?, ?, ?)",
                        (d, i, title, done),
                    )

            cur.execute("DROP TABLE goals_old")

        conn.commit()


# -----------------------------
# Queries (date filtering)
# -----------------------------
def q_sessions_for_date(conn: sqlite3.Connection, d: str) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM sessions
        WHERE substr(start_ts,1,10)=?
        ORDER BY start_ts DESC
        """,
        (d,),
    ).fetchall()


def q_distractions_for_date(conn: sqlite3.Connection, d: str) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM distractions
        WHERE substr(ts,1,10)=?
        ORDER BY ts DESC
        """,
        (d,),
    ).fetchall()


def q_goals_for_date(conn: sqlite3.Connection, d: str) -> List[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM goals
        WHERE goal_date=?
        ORDER BY slot ASC
        """,
        (d,),
    ).fetchall()


def calc_goal_stats(goals: List[sqlite3.Row]) -> Tuple[int, int, int]:
    total = len(goals)
    done = sum(1 for g in goals if int(g["done"]) == 1)
    pct = int(round((done / total) * 100)) if total > 0 else 0
    return done, total, pct


def calc_session_stats(sessions: List[sqlite3.Row]) -> Tuple[int, int]:
    count = len(sessions)
    total_min = sum(int(s["minutes"]) for s in sessions)
    return count, total_min


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def index():
    ensure_schema()
    d = today_str()

    with get_db() as conn:
        goals = q_goals_for_date(conn, d)
        distractions = q_distractions_for_date(conn, d)
        sessions = q_sessions_for_date(conn, d)

    return render_template(
        "index.html",
        date=d,
        goals=goals,
        distractions=distractions,
        sessions=sessions,
        app_name=APP_NAME,
    )


@app.post("/goals")
def save_goals():
    ensure_schema()
    d = today_str()

    titles = [
        (1, (request.form.get("g1") or "").strip()),
        (2, (request.form.get("g2") or "").strip()),
        (3, (request.form.get("g3") or "").strip()),
    ]

    with get_db() as conn:
        # 기존 goal의 done 유지하면서 title만 업데이트 (빈 문자열이면 해당 slot 삭제)
        existing = {int(r["slot"]): r for r in q_goals_for_date(conn, d)}

        for slot, title in titles:
            if title:
                done = int(existing.get(slot, {}).get("done", 0)) if slot in existing else 0
                conn.execute(
                    "INSERT OR REPLACE INTO goals(goal_date, slot, title, done) VALUES (?, ?, ?, ?)",
                    (d, slot, title, done),
                )
            else:
                conn.execute("DELETE FROM goals WHERE goal_date=? AND slot=?", (d, slot))

        conn.commit()

    return redirect(url_for("index"))


@app.post("/goals/<int:goal_id>/toggle")
def toggle_goal(goal_id: int):
    ensure_schema()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
        if row:
            new_done = 0 if int(row["done"]) == 1 else 1
            conn.execute("UPDATE goals SET done=? WHERE id=?", (new_done, goal_id))
            conn.commit()
    return redirect(url_for("index"))


@app.post("/distractions")
def add_distraction():
    ensure_schema()
    note = (request.form.get("note") or "").strip()
    if not note:
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute("INSERT INTO distractions(ts, note) VALUES(?,?)", (iso_now_local(), note))
        conn.commit()

    return redirect(url_for("index"))


@app.post("/sessions")
def add_session():
    ensure_schema()
    start_ts = (request.form.get("start_ts") or "").strip()
    end_ts = (request.form.get("end_ts") or "").strip()
    minutes = int((request.form.get("minutes") or "0").strip() or "0")

    if not start_ts or not end_ts or minutes <= 0:
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions(start_ts, end_ts, minutes) VALUES(?,?,?)",
            (start_ts, end_ts, minutes),
        )
        conn.commit()

    return redirect(url_for("index"))


@app.get("/report")
def report():
    ensure_schema()

    # v0.2: 날짜 선택 + 주간(range=week)
    q_date = parse_date(request.args.get("date"), today_str())
    range_mode = (request.args.get("range") or "day").strip()

    with get_db() as conn:
        if range_mode == "week":
            # end = q_date, 7일(포함)로 구성
            end = datetime.strptime(q_date, "%Y-%m-%d").date()
            days = [(end - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

            week_rows: List[Dict[str, Any]] = []
            for d in days:
                goals = q_goals_for_date(conn, d)
                sessions = q_sessions_for_date(conn, d)
                distractions = q_distractions_for_date(conn, d)

                g_done, g_total, g_pct = calc_goal_stats(goals)
                s_count, s_total_min = calc_session_stats(sessions)
                dis_count = len(distractions)

                week_rows.append(
                    {
                        "date": d,
                        "goal_done": g_done,
                        "goal_total": g_total,
                        "goal_pct": g_pct,
                        "session_count": s_count,
                        "focus_min": s_total_min,
                        "distractions": dis_count,
                    }
                )

            # 주간 합계
            sum_focus = sum(r["focus_min"] for r in week_rows)
            sum_sessions = sum(r["session_count"] for r in week_rows)
            sum_dis = sum(r["distractions"] for r in week_rows)

            # 목표 완료율은 "주간 합산"으로 계산(0/0 방지)
            sum_goal_done = sum(r["goal_done"] for r in week_rows)
            sum_goal_total = sum(r["goal_total"] for r in week_rows)
            sum_goal_pct = int(round((sum_goal_done / sum_goal_total) * 100)) if sum_goal_total > 0 else 0

            return render_template(
                "report.html",
                app_name=APP_NAME,
                mode="week",
                date=q_date,
                week_rows=week_rows,
                summary={
                    "focus_min": sum_focus,
                    "session_count": sum_sessions,
                    "distractions": sum_dis,
                    "goal_done": sum_goal_done,
                    "goal_total": sum_goal_total,
                    "goal_pct": sum_goal_pct,
                },
            )

        # day mode
        goals = q_goals_for_date(conn, q_date)
        sessions = q_sessions_for_date(conn, q_date)
        distractions = q_distractions_for_date(conn, q_date)

    g_done, g_total, g_pct = calc_goal_stats(goals)
    s_count, s_total_min = calc_session_stats(sessions)

    return render_template(
        "report.html",
        app_name=APP_NAME,
        mode="day",
        date=q_date,
        goals=goals,
        sessions=sessions,
        distractions=distractions,
        summary={
            "focus_min": s_total_min,
            "session_count": s_count,
            "distractions": len(distractions),
            "goal_done": g_done,
            "goal_total": g_total,
            "goal_pct": g_pct,
        },
    )


if __name__ == "__main__":
    ensure_schema()
    app.run(host=HOST, port=PORT, debug=DEBUG)