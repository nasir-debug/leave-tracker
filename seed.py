"""Creates an initial admin account and a few sample employees, including
some sample leave requests that demonstrate the running balance and the
holiday/sickness limit flags. Safe to re-run: skips anything that already
exists (matched by email).
"""

from datetime import date, timedelta

from server.db import init_db, get_db
from server.auth import hash_password
from app import app


def upsert_user(db, name, email, password, role, allowance, carry_over, start_date,
                 sickness_alert_days=None, sickness_alert_occurrences=None):
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return existing["id"]
    cur = db.execute(
        """INSERT INTO users
           (name, email, password_hash, role, holiday_allowance_days, carry_over_days,
            sickness_alert_days, sickness_alert_occurrences, start_date, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (name, email, hash_password(password), role, allowance, carry_over,
         sickness_alert_days, sickness_alert_occurrences, start_date),
    )
    db.commit()
    return cur.lastrowid


def add_leave(db, user_id, leave_type, start, end, days, status, notes=None):
    existing = db.execute(
        "SELECT id FROM leave_requests WHERE user_id = ? AND start_date = ? AND type = ?",
        (user_id, start, leave_type),
    ).fetchone()
    if existing:
        return
    decided = ", decided_by, decided_at" if status != "pending" else ""
    decided_vals = [user_id, date.today().isoformat()] if status != "pending" else []
    db.execute(
        f"""INSERT INTO leave_requests (user_id, type, start_date, end_date, days, status, notes{decided})
            VALUES (?, ?, ?, ?, ?, ?, ?{',?' * len(decided_vals)})""",
        [user_id, leave_type, start, end, days, status, notes] + decided_vals,
    )
    db.commit()


def run():
    with app.app_context():
        init_db(app)
        db = get_db()

        admin_id = upsert_user(
            db, "Alex Admin", "admin@example.com", "admin123",
            "admin", 25, 0, "2020-01-01",
        )
        jamie_id = upsert_user(
            db, "Jamie Chen", "jamie@example.com", "password123",
            "employee", 25, 3, "2022-03-01",
        )
        priya_id = upsert_user(
            db, "Priya Patel", "priya@example.com", "password123",
            "employee", 20, 0, "2023-06-15",
        )
        sam_id = upsert_user(
            db, "Sam Okafor", "sam@example.com", "password123",
            "employee", 28, 5, "2019-09-01",
            sickness_alert_days=5, sickness_alert_occurrences=2,
        )

        today = date.today()

        def iso(d):
            return d.isoformat()

        # Jamie: some approved holiday already taken this year, plus a pending request.
        add_leave(db, jamie_id, "holiday", iso(today - timedelta(days=40)),
                  iso(today - timedelta(days=36)), 5, "approved", "Spring break")
        add_leave(db, jamie_id, "holiday", iso(today + timedelta(days=14)),
                  iso(today + timedelta(days=18)), 5, "pending", "Summer trip")

        # Priya: near her (lower) allowance limit.
        add_leave(db, priya_id, "holiday", iso(today - timedelta(days=100)),
                  iso(today - timedelta(days=80)), 15, "approved", "Long trip home")

        # Sam: sickness pattern that should trip the lower per-employee threshold (>5 days or >2 episodes/12mo).
        add_leave(db, sam_id, "sickness", iso(today - timedelta(days=200)),
                  iso(today - timedelta(days=199)), 2, "approved", "Flu")
        add_leave(db, sam_id, "sickness", iso(today - timedelta(days=90)),
                  iso(today - timedelta(days=89)), 2, "approved", "Migraine")
        add_leave(db, sam_id, "sickness", iso(today - timedelta(days=10)),
                  iso(today - timedelta(days=8)), 3, "approved", "Back pain")

        print("Seed complete.")
        print("  admin@example.com / admin123  (admin)")
        print("  jamie@example.com / password123")
        print("  priya@example.com / password123")
        print("  sam@example.com   / password123  (sickness threshold should be flagged)")


if __name__ == "__main__":
    run()
