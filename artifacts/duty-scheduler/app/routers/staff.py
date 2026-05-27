from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import Optional
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()


def get_db():
    from app.database import get_db as _get_db
    return _get_db()


@router.get("/staff")
def staff_list(request: Request):
    conn = get_db()
    rows = conn.execute("""
        SELECT s.*,
               COUNT(da.id) as total_assignments
        FROM staff s
        LEFT JOIN duty_assignments da ON da.staff_id = s.id
        GROUP BY s.id
        ORDER BY s.name
    """).fetchall()
    conn.close()
    return templates.TemplateResponse("staff.html", {
        "request": request,
        "staff": rows,
        "active_page": "staff"
    })


@router.post("/staff")
def create_staff(
    request: Request,
    name: str = Form(...),
    rank: str = Form(""),
    staff_type: str = Form("contract"),
    status: str = Form("available"),
    restriction_type: Optional[str] = Form(None)
):
    conn = get_db()
    conn.execute("""
        INSERT INTO staff (name, rank, staff_type, status, restriction_type)
        VALUES (?, ?, ?, ?, ?)
    """, (name.strip(), rank.strip(), staff_type, status,
          restriction_type.strip() if restriction_type else None))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/staff", status_code=303)


@router.post("/staff/{staff_id}/status")
def update_status(
    staff_id: int,
    status: str = Form(...),
    restriction_type: Optional[str] = Form(None)
):
    conn = get_db()
    conn.execute(
        "UPDATE staff SET status = ?, restriction_type = ? WHERE id = ?",
        (status, restriction_type.strip() if restriction_type else None, staff_id)
    )
    conn.execute("""
        INSERT INTO staff_status_log (staff_id, status, from_date)
        VALUES (?, ?, date('now'))
    """, (staff_id, status))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/staff", status_code=303)


@router.post("/staff/{staff_id}/delete")
def delete_staff(staff_id: int):
    conn = get_db()
    conn.execute("DELETE FROM duty_assignments WHERE staff_id = ?", (staff_id,))
    conn.execute("DELETE FROM activities WHERE staff_id = ?", (staff_id,))
    conn.execute("DELETE FROM daily_plan WHERE staff_id = ?", (staff_id,))
    conn.execute("DELETE FROM staff_status_log WHERE staff_id = ?", (staff_id,))
    conn.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/staff", status_code=303)
