import calendar as pycalendar
from datetime import date

from flask import Blueprint, request, jsonify, g

from ..db import get_db
from ..auth import require_auth
from ..utils.balance import compute_holiday_balance, compute_sickness_status

bp = Blueprint("calendar_routes", __name__, url_prefix="/api/calendar")


@bp.get("")
@require_auth
def get_calendar():
    month_param = request.args.get("month")  # "YYYY-MM"
    if month_param:
        try:
            year, month = (int(p) for p in month_param.split("-"))
        except ValueError:
            return jsonify({"error": "month must be in YYYY-MM format"}), 400
    else:
        today = date.today()
        year, month = today.year, today.month

    last_day = pycalendar.monthrange(year, month)[1]
    range_start = f"{year:04d}-{month:02d}-01"
    range_end = f"{year:04d}-{month:02d}-{last_day:02d}"

    db = get_db()
    rows = db.execute(
        """SELECT lr.*, u.name AS user_name FROM leave_requests lr
           JOIN users u ON u.id = lr.user_id
           WHERE lr.start_date <= ? AND lr.end_date >= ?
             AND lr.status IN ('approved', 'pending')
           ORDER BY lr.start_date""",
        (range_end, range_start),
    ).fetchall()

    is_admin = g.current_user["role"] == "admin"
    flagged_cache = {}

    entries = []
    for row in rows:
        user_id = row["user_id"]
        if user_id not in flagged_cache:
            user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row["type"] == "holiday":
                flag = compute_holiday_balance(db, user)["over_limit"]
            else:
                flag = compute_sickness_status(db, user)["flagged"]
            flagged_cache[user_id] = flag

        entries.append({
            "id": row["id"],
            "user_id": user_id,
            "user_name": row["user_name"],
            "type": row["type"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "days": row["days"],
            "status": row["status"],
            "notes": row["notes"] if (is_admin or user_id == g.current_user["id"]) else None,
            "user_flagged": flagged_cache[user_id],
        })

    return jsonify({"year": year, "month": month, "entries": entries})
