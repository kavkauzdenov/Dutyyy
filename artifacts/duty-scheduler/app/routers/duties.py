from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import Optional
from datetime import date
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()


def get_db():
    from app.database import get_db as _get_db
    return _get_db()


@router.get("/duties")
def duties_list(request: Request, duty_date: Optional[str] = None):
    if not duty_date:
        duty_date = date.today().isoformat()
    conn = get_db()

    duty_types = conn.execute("SELECT * FROM duty_types ORDER BY category DESC, name").fetchall()

    duties = conn.execute("""
        SELECT d.*, dt.name as type_name, dt.category,
               COUNT(da.id) as assigned_count,
               GROUP_CONCAT(s.name || ' ' || s.rank, ', ') as assigned_names
        FROM duties d
        JOIN duty_types dt ON dt.id = d.duty_type_id
        LEFT JOIN duty_assignments da ON da.duty_id = d.id
        LEFT JOIN staff s ON s.id = da.staff_id
        WHERE d.duty_date = ?
        GROUP BY d.id
        ORDER BY dt.category DESC, d.start_time
    """, (duty_date,)).fetchall()

    conn.close()
    return templates.TemplateResponse("duties.html", {
        "request": request,
        "duties": duties,
        "duty_types": duty_types,
        "duty_date": duty_date,
        "active_page": "duties"
    })


@router.post("/duties")
def create_duty(
    duty_type_id: int = Form(...),
    duty_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    min_staff: int = Form(1),
    notes: str = Form("")
):
    conn = get_db()
    dt_row = conn.execute("SELECT min_staff FROM duty_types WHERE id = ?", (duty_type_id,)).fetchone()
    actual_min = max(min_staff, dt_row["min_staff"] if dt_row else 1)
    conn.execute("""
        INSERT INTO duties (duty_type_id, duty_date, start_time, end_time, min_staff, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (duty_type_id, duty_date, start_time, end_time, actual_min, notes))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/duties?duty_date={duty_date}", status_code=303)


@router.post("/duties/{duty_id}/delete")
def delete_duty(duty_id: int, duty_date: str = Form(...)):
    conn = get_db()
    conn.execute("DELETE FROM duty_assignments WHERE duty_id = ?", (duty_id,))
    conn.execute("DELETE FROM daily_plan WHERE duty_id = ?", (duty_id,))
    conn.execute("DELETE FROM duties WHERE id = ?", (duty_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/duties?duty_date={duty_date}", status_code=303)


@router.post("/duties/{duty_id}/assign")
def manual_assign(duty_id: int, staff_id: int = Form(...), duty_date: str = Form(...)):
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO duty_assignments (duty_id, staff_id) VALUES (?, ?)",
            (duty_id, staff_id)
        )
        d = conn.execute("SELECT start_time, end_time, duty_date FROM duties WHERE id = ?", (duty_id,)).fetchone()
        if d:
            from app.scheduler.engine import duty_hours
            dh = duty_hours(d["start_time"], d["end_time"])
            conn.execute(
                "UPDATE staff SET total_duty_hours = total_duty_hours + ? WHERE id = ?",
                (dh, staff_id)
            )
            conn.execute("""
                INSERT OR REPLACE INTO daily_plan (plan_date, staff_id, assignment_type, duty_id, activity_id)
                VALUES (?, ?, 'duty', ?, NULL)
            """, (d["duty_date"], staff_id, duty_id))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return RedirectResponse(url=f"/duties?duty_date={duty_date}", status_code=303)


@router.post("/duty_types")
def create_duty_type(
    name: str = Form(...),
    category: str = Form("mandatory"),
    min_staff: int = Form(1),
    description: str = Form("")
):
    conn = get_db()
    conn.execute("""
        INSERT INTO duty_types (name, category, min_staff, description)
        VALUES (?, ?, ?, ?)
    """, (name.strip(), category, min_staff, description))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/duties", status_code=303)


@router.post("/duty_types/{type_id}/delete")
def delete_duty_type(type_id: int):
    conn = get_db()
    conn.execute("DELETE FROM duty_types WHERE id = ?", (type_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/duties", status_code=303)
