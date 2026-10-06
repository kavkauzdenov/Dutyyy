from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import date
import os

from app.database import init_db
from app.routers import staff, duties, schedule, settings as settings_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Система нарядов")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.include_router(staff.router)
app.include_router(duties.router)
app.include_router(schedule.router)
app.include_router(settings_router.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard(request: Request):
    from app.database import get_db
    conn = get_db()
    today = date.today().isoformat()

    duties_today = conn.execute("""
        SELECT d.id, d.start_time, d.end_time, d.min_staff,
               dt.name as type_name, dt.category,
               COUNT(da.id) as assigned_count
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import date
import os

from app.database import init_db
from app.routers import staff, duties, schedule, settings as settings_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Система нарядов")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.include_router(staff.router)
app.include_router(duties.router)
app.include_router(schedule.router)
app.include_router(settings_router.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard(request: Request):
    from app.database import get_db
    conn = get_db()
    today = date.today().isoformat()

    duties_today = conn.execute("""
        SELECT d.id, d.start_time, d.end_time, d.min_staff,
               dt.name as type_name, dt.category,
               COUNT(da.id) as assigned_count
        FROM duties d
        JOIN duty_types dt ON dt.id = d.duty_type_id
        LEFT JOIN duty_assignments da ON da.duty_id = d.id
        WHERE d.duty_date = ?
        GROUP BY d.id
        ORDER BY dt.category DESC, d.start_time
    """, (today,)).fetchall()

    total_staff = conn.execute("SELECT COUNT(*) FROM staff WHERE status NOT IN ('exempt')").fetchone()[0]
    available = conn.execute(
        "SELECT COUNT(*) FROM staff WHERE status = 'available'"
    ).fetchone()[0]
    sick = conn.execute("SELECT COUNT(*) FROM staff WHERE status = 'sick'").fetchone()[0]
    on_leave = conn.execute(
        "SELECT COUNT(*) FROM staff WHERE status IN ('vacation','business_trip')"
    ).fetchone()[0]

    on_duty_today = conn.execute("""
        SELECT COUNT(DISTINCT da.staff_id) FROM duty_assignments da
        JOIN duties d ON d.id = da.duty_id WHERE d.duty_date = ?
    """, (today,)).fetchone()[0]

    shortages = []
    for d in duties_today:
        gap = d["min_staff"] - d["assigned_count"]
        if gap > 0:
            shortages.append({
                "type": d["type_name"],
                "start": d["start_time"],
                "end": d["end_time"],
                "missing": gap
            })

    mandatory = [d for d in duties_today if d["category"] == "mandatory"]
    additional = [d for d in duties_today if d["category"] == "additional"]

    recent_plan = conn.execute("""
        SELECT s.name, s.rank, dp.assignment_type,
               dt.name as duty_name,
               a.activity_type
        FROM daily_plan dp
        JOIN staff s ON s.id = dp.staff_id
        LEFT JOIN duties du ON du.id = dp.duty_id
        LEFT JOIN duty_types dt ON dt.id = du.duty_type_id
        LEFT JOIN activities a ON a.id = dp.activity_id
        WHERE dp.plan_date = ?
        ORDER BY dp.assignment_type, s.name
    """, (today,)).fetchall()

    conn.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "today": today,
        "total_staff": total_staff,
        "available": available,
        "sick": sick,
        "on_leave": on_leave,
        "on_duty_today": on_duty_today,
        "mandatory": mandatory,
        "additional": additional,
        "shortages": shortages,
        "recent_plan": recent_plan,
        "active_page": "dashboard"
    })

        FROM duties d
        JOIN duty_types dt ON dt.id = d.duty_type_id
        LEFT JOIN duty_assignments da ON da.duty_id = d.id
        WHERE d.duty_date = ?
        GROUP BY d.id
        ORDER BY dt.category DESC, d.start_time
    """, (today,)).fetchall()

    total_staff = conn.execute("SELECT COUNT(*) FROM staff WHERE status NOT IN ('exempt')").fetchone()[0]
    available = conn.execute(
        "SELECT COUNT(*) FROM staff WHERE status = 'available'"
    ).fetchone()[0]
    sick = conn.execute("SELECT COUNT(*) FROM staff WHERE status = 'sick'").fetchone()[0]
    on_leave = conn.execute(
        "SELECT COUNT(*) FROM staff WHERE status IN ('vacation','business_trip')"
    ).fetchone()[0]

    on_duty_today = conn.execute("""
        SELECT COUNT(DISTINCT da.staff_id) FROM duty_assignments da
        JOIN duties d ON d.id = da.duty_id WHERE d.duty_date = ?
    """, (today,)).fetchone()[0]

    shortages = []
    for d in duties_today:
        gap = d["min_staff"] - d["assigned_count"]
        if gap > 0:
            shortages.append({
                "type": d["type_name"],
                "start": d["start_time"],
                "end": d["end_time"],
                "missing": gap
            })

    mandatory = [d for d in duties_today if d["category"] == "mandatory"]
    additional = [d for d in duties_today if d["category"] == "additional"]

    recent_plan = conn.execute("""
        SELECT s.name, s.rank, dp.assignment_type,
               dt.name as duty_name,
               a.activity_type
        FROM daily_plan dp
        JOIN staff s ON s.id = dp.staff_id
        LEFT JOIN duties du ON du.id = dp.duty_id
        LEFT JOIN duty_types dt ON dt.id = du.duty_type_id
        LEFT JOIN activities a ON a.id = dp.activity_id
        WHERE dp.plan_date = ?
        ORDER BY dp.assignment_type, s.name
    """, (today,)).fetchall()

    conn.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "today": today,
        "total_staff": total_staff,
        "available": available,
        "sick": sick,
        "on_leave": on_leave,
        "on_duty_today": on_duty_today,
        "mandatory": mandatory,
        "additional": additional,
        "shortages": shortages,
        "recent_plan": recent_plan,
        "active_page": "dashboard"
    })
