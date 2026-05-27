from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from datetime import date
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()


def get_db():
    from app.database import get_db as _get_db
    return _get_db()


@router.get("/daily-plan")
def daily_plan(request: Request, plan_date: str = None):
    if not plan_date:
        plan_date = date.today().isoformat()
    conn = get_db()

    all_staff = conn.execute("SELECT * FROM staff ORDER BY name").fetchall()

    plan = conn.execute("""
        SELECT dp.*, s.name as staff_name, s.rank, s.staff_type,
               dt.name as duty_name, dt.category,
               du.start_time, du.end_time,
               a.activity_type
        FROM daily_plan dp
        JOIN staff s ON s.id = dp.staff_id
        LEFT JOIN duties du ON du.id = dp.duty_id
        LEFT JOIN duty_types dt ON dt.id = du.duty_type_id
        LEFT JOIN activities a ON a.id = dp.activity_id
        WHERE dp.plan_date = ?
        ORDER BY dp.assignment_type, s.name
    """, (plan_date,)).fetchall()

    planned_ids = {row["staff_id"] for row in plan}
    unplanned = [s for s in all_staff if s["id"] not in planned_ids and s["status"] != "exempt"]

    conn.close()
    return templates.TemplateResponse("daily_plan.html", {
        "request": request,
        "plan": plan,
        "unplanned": unplanned,
        "plan_date": plan_date,
        "active_page": "daily-plan"
    })


@router.post("/generate_schedule")
def generate_schedule(plan_date: str = Form(...)):
    from app.scheduler.engine import generate_schedule as _gen
    _gen(plan_date)
    return RedirectResponse(url=f"/daily-plan?plan_date={plan_date}", status_code=303)


@router.get("/schedule/day/{target_date}")
def get_schedule_api(target_date: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT dp.*, s.name as staff_name, s.rank,
               dt.name as duty_name,
               du.start_time, du.end_time,
               a.activity_type
        FROM daily_plan dp
        JOIN staff s ON s.id = dp.staff_id
        LEFT JOIN duties du ON du.id = dp.duty_id
        LEFT JOIN duty_types dt ON dt.id = du.duty_type_id
        LEFT JOIN activities a ON a.id = dp.activity_id
        WHERE dp.plan_date = ?
    """, (target_date,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/daily-plan/clear")
def clear_plan(plan_date: str = Form(...)):
    conn = get_db()
    conn.execute("DELETE FROM daily_plan WHERE plan_date = ?", (plan_date,))
    conn.execute("DELETE FROM activities WHERE activity_date = ?", (plan_date,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/daily-plan?plan_date={plan_date}", status_code=303)
