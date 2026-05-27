from datetime import datetime, date, timedelta
import sqlite3
from app.database import get_db


UNAVAILABLE_STATUSES = {"sick", "vacation", "business_trip", "exempt"}


def parse_time(t: str) -> float:
    """Convert HH:MM to float hours from midnight."""
    h, m = map(int, t.split(":"))
    return h + m / 60.0


def duty_hours(start: str, end: str) -> float:
    s = parse_time(start)
    e = parse_time(end)
    if e <= s:
        e += 24
    return e - s


def get_staff_hours_on_date(conn, staff_id: int, target_date: str) -> float:
    """Sum of duty hours assigned on a calendar date (midnight-to-midnight)."""
    cur = conn.execute("""
        SELECT d.start_time, d.end_time
        FROM duty_assignments da
        JOIN duties d ON d.id = da.duty_id
        WHERE da.staff_id = ? AND d.duty_date = ?
    """, (staff_id, target_date))
    total = 0.0
    for row in cur.fetchall():
        total += duty_hours(row["start_time"], row["end_time"])
    return total


def get_last_duty_end(conn, staff_id: int, before_date: str) -> float | None:
    """Return the end time (as float hours) of the most recent duty ending before or on before_date."""
    cur = conn.execute("""
        SELECT d.duty_date, d.start_time, d.end_time
        FROM duty_assignments da
        JOIN duties d ON d.id = da.duty_id
        WHERE da.staff_id = ?
        ORDER BY d.duty_date DESC, d.end_time DESC
        LIMIT 5
    """, (staff_id,))
    rows = cur.fetchall()
    if not rows:
        return None

    target = datetime.strptime(before_date, "%Y-%m-%d")
    best_end_dt = None

    for row in rows:
        s = parse_time(row["start_time"])
        e = parse_time(row["end_time"])
        d_date = datetime.strptime(row["duty_date"], "%Y-%m-%d")

        start_dt = d_date + timedelta(hours=s)
        if e <= s:
            end_dt = d_date + timedelta(hours=e + 24)
        else:
            end_dt = d_date + timedelta(hours=e)

        if end_dt <= datetime.strptime(before_date + " 23:59", "%Y-%m-%d %H:%M"):
            if best_end_dt is None or end_dt > best_end_dt:
                best_end_dt = end_dt

    return best_end_dt


def can_assign(conn, staff_id: int, duty: sqlite3.Row, rules: sqlite3.Row) -> bool:
    """Check all constraints before assigning a staff member to a duty."""
    target_date = duty["duty_date"]
    start_str = duty["start_time"]
    end_str = duty["end_time"]
    dh = duty_hours(start_str, end_str)

    hours_today = get_staff_hours_on_date(conn, staff_id, target_date)
    if hours_today + dh > rules["max_hours_per_day"]:
        return False

    last_end_dt = get_last_duty_end(conn, staff_id, target_date)
    if last_end_dt is not None:
        duty_start_dt = datetime.strptime(target_date, "%Y-%m-%d") + timedelta(hours=parse_time(start_str))
        gap = (duty_start_dt - last_end_dt).total_seconds() / 3600.0
        if gap < rules["min_rest_hours"]:
            return False

    return True


def get_staff_duty_count(conn, staff_id: int, month: str) -> int:
    cur = conn.execute("""
        SELECT COUNT(*) FROM duty_assignments da
        JOIN duties d ON d.id = da.duty_id
        WHERE da.staff_id = ? AND strftime('%Y-%m', d.duty_date) = ?
    """, (staff_id, month))
    return cur.fetchone()[0]


def generate_schedule(target_date: str) -> dict:
    conn = get_db()
    results = {"assigned": [], "warnings": [], "date": target_date}

    rules_row = conn.execute("SELECT * FROM duty_rules LIMIT 1").fetchone()
    if not rules_row:
        conn.close()
        results["warnings"].append("Правила нарядов не настроены")
        return results

    duties = conn.execute("""
        SELECT d.*, dt.name as type_name, dt.category, dt.id as dtype_id
        FROM duties d
        JOIN duty_types dt ON dt.id = d.duty_type_id
        WHERE d.duty_date = ?
        ORDER BY dt.category DESC, d.start_time ASC
    """, (target_date,)).fetchall()

    if not duties:
        conn.close()
        results["warnings"].append(f"Нет нарядов на {target_date}")
        return results

    all_staff = conn.execute("""
        SELECT * FROM staff
        WHERE status NOT IN ('sick','vacation','business_trip','exempt')
        ORDER BY total_duty_hours ASC, name ASC
    """).fetchall()

    if not all_staff:
        conn.close()
        results["warnings"].append("Нет доступных сотрудников")
        return results

    assigned_today = set()

    for duty in duties:
        existing = conn.execute(
            "SELECT staff_id FROM duty_assignments WHERE duty_id = ?",
            (duty["id"],)
        ).fetchall()
        already_assigned = {r["staff_id"] for r in existing}
        needed = duty["min_staff"] - len(already_assigned)

        if needed <= 0:
            continue

        candidates = []
        for s in all_staff:
            if s["id"] in already_assigned:
                continue
            if s["status"] == "restricted":
                if s["restriction_type"] and s["restriction_type"] != duty["type_name"]:
                    continue
            if can_assign(conn, s["id"], duty, rules_row):
                candidates.append(s)

        candidates.sort(key=lambda s: (
            s["id"] in assigned_today,
            s["total_duty_hours"]
        ))

        filled = 0
        for candidate in candidates:
            if filled >= needed:
                break
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO duty_assignments (duty_id, staff_id) VALUES (?, ?)",
                    (duty["id"], candidate["id"])
                )
                dh = duty_hours(duty["start_time"], duty["end_time"])
                conn.execute(
                    "UPDATE staff SET total_duty_hours = total_duty_hours + ? WHERE id = ?",
                    (dh, candidate["id"])
                )
                conn.execute("""
                    INSERT OR REPLACE INTO daily_plan (plan_date, staff_id, assignment_type, duty_id, activity_id)
                    VALUES (?, ?, 'duty', ?, NULL)
                """, (target_date, candidate["id"], duty["id"]))

                results["assigned"].append({
                    "staff": candidate["name"],
                    "duty": duty["type_name"],
                    "start": duty["start_time"],
                    "end": duty["end_time"]
                })
                assigned_today.add(candidate["id"])
                filled += 1
            except Exception as e:
                results["warnings"].append(f"Ошибка при назначении {candidate['name']}: {e}")

        if filled < needed:
            results["warnings"].append(
                f"Наряд '{duty['type_name']}' {duty['start_time']}-{duty['end_time']}: "
                f"назначено {filled}/{needed} (недобор {needed - filled})"
            )

    free_staff = [s for s in all_staff if s["id"] not in assigned_today]
    activity_types = ["training", "maintenance", "admin", "rest"]

    month = target_date[:7]
    day_of_week = datetime.strptime(target_date, "%Y-%m-%d").weekday()

    for i, s in enumerate(free_staff):
        existing_plan = conn.execute(
            "SELECT id FROM daily_plan WHERE plan_date = ? AND staff_id = ?",
            (target_date, s["id"])
        ).fetchone()
        if existing_plan:
            continue

        rest_days_month = conn.execute("""
            SELECT COUNT(*) FROM daily_plan
            WHERE staff_id = ? AND strftime('%Y-%m', plan_date) = ?
            AND assignment_type = 'rest'
        """, (s["id"], month)).fetchone()[0]

        rest_days_week = conn.execute("""
            SELECT COUNT(*) FROM daily_plan
            WHERE staff_id = ?
            AND plan_date >= date(?, '-6 days')
            AND plan_date <= ?
            AND assignment_type = 'rest'
        """, (s["id"], target_date, target_date)).fetchone()[0]

        needs_rest = (
            (rest_days_week < rules_row["min_weekly_rest"] and day_of_week >= 5) or
            (s["staff_type"] != "conscript" and rest_days_month < rules_row["min_monthly_rest"])
        )

        if needs_rest:
            act_type = "rest"
        else:
            act_type = activity_types[i % 3]

        act_id = conn.execute("""
            INSERT INTO activities (staff_id, activity_date, activity_type)
            VALUES (?, ?, ?)
        """, (s["id"], target_date, act_type)).lastrowid

        conn.execute("""
            INSERT OR REPLACE INTO daily_plan (plan_date, staff_id, assignment_type, duty_id, activity_id)
            VALUES (?, ?, ?, NULL, ?)
        """, (target_date, s["id"], act_type, act_id))

    conn.commit()
    conn.close()
    return results
