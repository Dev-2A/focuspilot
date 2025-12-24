import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import connect, init_db, today_str, report_summary, list_goals, upsert_goals, toggle_goal
from .db import add_distraction, list_distractions, add_session, list_sessions, now_iso

def create_app() -> FastAPI:
    app = FastAPI(title="FocusPilot", version="0.1.0")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))
    
    db_path = os.getenv("FOCUSPILOT_DB", "focuspilot.db")
    conn = connect(db_path)
    init_db(conn)
    
    app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        date_s = today_str()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "date": date_s,
                "goals": list_goals(conn, date_s),
                "sessions": list_sessions(conn, date_s),
                "distractions": list_distractions(conn, date_s),
            },
        )
    
    @app.post("/goals")
    def save_goals(
        g1: str = Form(""),
        g2: str = Form(""),
        g3: str = Form(""),
    ):
        date_s = today_str()
        upsert_goals(conn, date_s, [g1, g2, g3])
        return RedirectResponse("/", status_code=303)
    
    @app.post("/goals/{goal_id}/toggle")
    def goal_toggle(goal_id: int):
        toggle_goal(conn, goal_id)
        return RedirectResponse("/", status_code=303)
    
    @app.post("/distractions")
    def log_distraction(note: str = Form("")):
        date_s = today_str()
        add_distraction(conn, date_s, note)
        return RedirectResponse("/", status_code=303)
    
    @app.post("/sessions")
    def log_session(start_ts: str = Form(""), end_ts: str = Form(""), minutes: int = Form(0)):
        date_s = today_str()
        start_ts = start_ts.strip() or now_iso()
        end_ts = end_ts.strip() or now_iso()
        add_session(conn, date_s, start_ts, end_ts, int(minutes))
        return RedirectResponse("/", status_code=303)
    
    @app.get("/report", response_class=HTMLResponse)
    def report(request: Request):
        date_s = today_str()
        summary = report_summary(conn, date_s)
        return templates.TemplateResponse("report.html", {"request": request, "summary": summary})
    
    return app