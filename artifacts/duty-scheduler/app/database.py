import sqlite3
import os

DB_PATH = os.environ.get("DATABASE_PATH", "/tmp/dutyyy-demo.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rank TEXT NOT NULL DEFAULT '',
            staff_type TEXT NOT NULL DEFAULT 'contract',
            status TEXT NOT NULL DEFAULT 'available',
            restriction_type TEXT DEFAULT NULL,
            total_duty_hours REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS duty_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'mandatory',
            min_staff INTEGER NOT NULL DEFAULT 1,
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS duties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duty_type_id INTEGER NOT NULL REFERENCES duty_types(id),
            duty_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            min_staff INTEGER NOT NULL DEFAULT 1,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS duty_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duty_id INTEGER NOT NULL REFERENCES duties(id),
            staff_id INTEGER NOT NULL REFERENCES staff(id),
            assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(duty_id, staff_id)
        );

        CREATE TABLE IF NOT EXISTS staff_status_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES staff(id),
            status TEXT NOT NULL,
            reason TEXT DEFAULT '',
            from_date TEXT NOT NULL,
            to_date TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES staff(id),
            activity_date TEXT NOT NULL,
            activity_type TEXT NOT NULL DEFAULT 'training',
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS daily_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_date TEXT NOT NULL,
            staff_id INTEGER NOT NULL REFERENCES staff(id),
            assignment_type TEXT NOT NULL,
            duty_id INTEGER REFERENCES duties(id),
            activity_id INTEGER REFERENCES activities(id),
            UNIQUE(plan_date, staff_id)
        );

        CREATE TABLE IF NOT EXISTS duty_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mandatory_per_day INTEGER NOT NULL DEFAULT 2,
            additional_per_day INTEGER NOT NULL DEFAULT 1,
            min_staff_mandatory INTEGER NOT NULL DEFAULT 2,
            min_staff_additional INTEGER NOT NULL DEFAULT 1,
            max_hours_per_day REAL NOT NULL DEFAULT 8,
            min_rest_hours REAL NOT NULL DEFAULT 4,
            min_weekly_rest INTEGER NOT NULL DEFAULT 1,
            min_monthly_rest INTEGER NOT NULL DEFAULT 6
        );
    """)

    cur.execute("SELECT COUNT(*) FROM duty_rules")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO duty_rules (mandatory_per_day, additional_per_day,
                min_staff_mandatory, min_staff_additional,
                max_hours_per_day, min_rest_hours,
                min_weekly_rest, min_monthly_rest)
            VALUES (2, 1, 2, 1, 8, 4, 1, 6)
        """)

    conn.commit()
    conn.close()

