import sqlite3
import os
from flask import g
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'employee')),
    holiday_allowance_days REAL NOT NULL DEFAULT 25,
    carry_over_days REAL NOT NULL DEFAULT 0,
    sickness_alert_days INTEGER,
    sickness_alert_occurrences INTEGER,
    start_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type TEXT NOT NULL CHECK(type IN ('holiday', 'sickness')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    days REAL NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')),
    notes TEXT,
    decided_by INTEGER REFERENCES users(id),
    decided_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS org_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    default_holiday_allowance_days REAL NOT NULL DEFAULT 25,
    default_carry_over_days REAL NOT NULL DEFAULT 0,
    sickness_alert_days INTEGER NOT NULL DEFAULT 10,
    sickness_alert_occurrences INTEGER NOT NULL DEFAULT 3
);
"""


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(config.DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript(SCHEMA)
    conn.execute(
        """INSERT OR IGNORE INTO org_settings
           (id, default_holiday_allowance_days, default_carry_over_days,
            sickness_alert_days, sickness_alert_occurrences)
           VALUES (1, ?, ?, ?, ?)""",
        (
            config.DEFAULT_HOLIDAY_ALLOWANCE_DAYS,
            config.DEFAULT_CARRY_OVER_DAYS,
            config.DEFAULT_SICKNESS_ALERT_DAYS,
            config.DEFAULT_SICKNESS_ALERT_OCCURRENCES,
        ),
    )
    conn.commit()
    conn.close()
    app.teardown_appcontext(close_db)


def bootstrap_admin():
    """Creates the first admin account from env vars if no users exist yet."""
    if not (config.BOOTSTRAP_ADMIN_EMAIL and config.BOOTSTRAP_ADMIN_PASSWORD):
        return
    from datetime import date
    from .auth import hash_password

    conn = sqlite3.connect(config.DB_PATH)
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing:
            return
        try:
            conn.execute(
                """INSERT INTO users
                   (name, email, password_hash, role, holiday_allowance_days, carry_over_days,
                    start_date, active)
                   VALUES (?, ?, ?, 'admin', ?, ?, ?, 1)""",
                (
                    config.BOOTSTRAP_ADMIN_NAME,
                    config.BOOTSTRAP_ADMIN_EMAIL.strip().lower(),
                    hash_password(config.BOOTSTRAP_ADMIN_PASSWORD),
                    config.DEFAULT_HOLIDAY_ALLOWANCE_DAYS,
                    config.DEFAULT_CARRY_OVER_DAYS,
                    date.today().isoformat(),
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Another worker process won the race and already created it.
            pass
    finally:
        conn.close()
