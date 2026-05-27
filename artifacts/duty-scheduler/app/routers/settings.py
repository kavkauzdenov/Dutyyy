from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()


def get_db():
    from app.database import get_db as _get_db
    return _get_db()


@router.get("/settings")
def settings_page(request: Request):
    conn = get_db()
    rules = conn.execute("SELECT * FROM duty_rules LIMIT 1").fetchone()
    duty_types = conn.execute("SELECT * FROM duty_types ORDER BY category DESC, name").fetchall()
    conn.close()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "rules": rules,
        "duty_types": duty_types,
        "active_page": "settings"
    })


@router.post("/settings/rules")
def update_rules(
    mandatory_per_day: int = Form(...),
    additional_per_day: int = Form(...),
    min_staff_mandatory: int = Form(...),
    min_staff_additional: int = Form(...),
    max_hours_per_day: float = Form(...),
    min_rest_hours: float = Form(...),
    min_weekly_rest: int = Form(...),
    min_monthly_rest: int = Form(...)
):
    conn = get_db()
    existing = conn.execute("SELECT id FROM duty_rules LIMIT 1").fetchone()
    if existing:
        conn.execute("""
            UPDATE duty_rules SET
                mandatory_per_day = ?,
                additional_per_day = ?,
                min_staff_mandatory = ?,
                min_staff_additional = ?,
                max_hours_per_day = ?,
                min_rest_hours = ?,
                min_weekly_rest = ?,
                min_monthly_rest = ?
            WHERE id = ?
        """, (mandatory_per_day, additional_per_day,
              min_staff_mandatory, min_staff_additional,
              max_hours_per_day, min_rest_hours,
              min_weekly_rest, min_monthly_rest, existing["id"]))
    else:
        conn.execute("""
            INSERT INTO duty_rules (mandatory_per_day, additional_per_day,
                min_staff_mandatory, min_staff_additional,
                max_hours_per_day, min_rest_hours,
                min_weekly_rest, min_monthly_rest)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (mandatory_per_day, additional_per_day,
              min_staff_mandatory, min_staff_additional,
              max_hours_per_day, min_rest_hours,
              min_weekly_rest, min_monthly_rest))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/settings", status_code=303)
