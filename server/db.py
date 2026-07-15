import json
import os
import sqlite3
import urllib.request

from flask import g

from . import config

GOV_UK_BANK_HOLIDAYS_URL = "https://www.gov.uk/bank-holidays.json"
BANK_HOLIDAY_DIVISION = "england-and-wales"
BANK_HOLIDAY_NOTE_PREFIX = "UK Bank Holiday:"

SQLITE_SCHEMA = """
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

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
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
    created_at TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type TEXT NOT NULL CHECK(type IN ('holiday', 'sickness')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    days REAL NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected')),
    notes TEXT,
    decided_by INTEGER REFERENCES users(id),
    decided_at TEXT,
    created_at TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')
);

CREATE TABLE IF NOT EXISTS org_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    default_holiday_allowance_days REAL NOT NULL DEFAULT 25,
    default_carry_over_days REAL NOT NULL DEFAULT 0,
    sickness_alert_days INTEGER NOT NULL DEFAULT 10,
    sickness_alert_occurrences INTEGER NOT NULL DEFAULT 3
);
"""


class PostgresConnection:
    """Thin wrapper so call sites can use sqlite3.Connection-style .execute()
    regardless of which backend is active. Placeholders are written as "?"
    throughout the app (sqlite style) and translated to "%s" here."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), tuple(params))
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _connect():
    if config.USE_POSTGRES:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(config.DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresConnection(conn)

    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert_returning_id(conn, sql, params):
    """Runs an INSERT and returns the new row's id, for either backend."""
    if config.USE_POSTGRES:
        cur = conn.execute(sql + " RETURNING id", params)
        return cur.fetchone()["id"]
    cur = conn.execute(sql, params)
    return cur.lastrowid


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    conn = _connect()
    if config.USE_POSTGRES:
        for statement in POSTGRES_SCHEMA.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)
        conn.execute(
            """INSERT INTO org_settings
               (id, default_holiday_allowance_days, default_carry_over_days,
                sickness_alert_days, sickness_alert_occurrences)
               VALUES (1, ?, ?, ?, ?)
               ON CONFLICT (id) DO NOTHING""",
            (
                config.DEFAULT_HOLIDAY_ALLOWANCE_DAYS,
                config.DEFAULT_CARRY_OVER_DAYS,
                config.DEFAULT_SICKNESS_ALERT_DAYS,
                config.DEFAULT_SICKNESS_ALERT_OCCURRENCES,
            ),
        )
    else:
        conn.executescript(SQLITE_SCHEMA)
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


def _admin_already_exists(conn):
    row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
    return bool((row["n"] if config.USE_POSTGRES else row[0]))


def bootstrap_admin():
    """Creates the first admin account from env vars if no users exist yet."""
    if not (config.BOOTSTRAP_ADMIN_EMAIL and config.BOOTSTRAP_ADMIN_PASSWORD):
        return
    from datetime import date
    from .auth import hash_password

    conn = _connect()
    try:
        if _admin_already_exists(conn):
            return

        insert_args = (
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

        if config.USE_POSTGRES:
            import psycopg2

            try:
                insert_returning_id(conn, *insert_args)
                conn.commit()
            except psycopg2.errors.UniqueViolation:
                # Another worker process won the race and already created it.
                conn.rollback()
        else:
            try:
                insert_returning_id(conn, *insert_args)
                conn.commit()
            except sqlite3.IntegrityError:
                pass
    finally:
        conn.close()


def _fetch_uk_bank_holidays(years):
    """Returns {year: [(iso_date, title), ...]} from gov.uk's official bank
    holidays feed, for England & Wales. Returns {} on any failure (network
    down, gov.uk unreachable, unexpected response shape) - this is a
    nice-to-have sync, never something that should block app startup."""
    try:
        with urllib.request.urlopen(GOV_UK_BANK_HOLIDAYS_URL, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        events = data[BANK_HOLIDAY_DIVISION]["events"]
    except Exception as e:
        print(f"[leave-tracker] bank holiday fetch failed: {e}", flush=True)
        return {}

    by_year = {y: [] for y in years}
    for ev in events:
        ev_date = ev.get("date", "")
        if ev_date[:4].isdigit() and int(ev_date[:4]) in by_year:
            by_year[int(ev_date[:4])].append((ev_date, ev.get("title", "Bank Holiday")))
    return by_year


def sync_bank_holidays():
    """Idempotently creates approved holiday leave records for every active
    employee for this year's and next year's UK (England & Wales) bank
    holidays. Skips any date before the employee's start_date, so joining
    mid-year doesn't retroactively dock days from before they were employed.
    Safe to call on every startup - already-synced dates are skipped."""
    from datetime import date

    today_year = date.today().year
    holidays_by_year = _fetch_uk_bank_holidays([today_year, today_year + 1])
    if not any(holidays_by_year.values()):
        return

    conn = _connect()
    try:
        users = conn.execute("SELECT * FROM users WHERE active = 1").fetchall()
        added = 0
        for holidays in holidays_by_year.values():
            for user in users:
                for holiday_date, title in holidays:
                    if holiday_date < user["start_date"]:
                        continue
                    existing = conn.execute(
                        "SELECT id FROM leave_requests WHERE user_id = ? AND start_date = ? AND notes LIKE ?",
                        (user["id"], holiday_date, f"{BANK_HOLIDAY_NOTE_PREFIX}%"),
                    ).fetchone()
                    if existing:
                        continue
                    conn.execute(
                        """INSERT INTO leave_requests
                           (user_id, type, start_date, end_date, days, status, notes, decided_at)
                           VALUES (?, 'holiday', ?, ?, 1, 'approved', ?, ?)""",
                        (user["id"], holiday_date, holiday_date, f"{BANK_HOLIDAY_NOTE_PREFIX} {title}", holiday_date),
                    )
                    added += 1
        conn.commit()
        if added:
            print(f"[leave-tracker] synced {added} UK bank holiday leave record(s)", flush=True)
    except Exception as e:
        print(f"[leave-tracker] bank holiday sync failed: {e}", flush=True)
        conn.rollback()
    finally:
        conn.close()