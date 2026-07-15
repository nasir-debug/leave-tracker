from datetime import datetime

from flask import Blueprint, request, jsonify, g

from ..db import get_db, insert_returning_id
from ..auth import require_auth, require_role
from ..utils.dates import count_business_days, parse_date
from ..utils.balance import compute_holiday_balance

bp = Blueprint("leave_routes", __name__, url_prefix="/api/leave")


def serialize_leave(row):
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "user_name": row["user_name"] if "user_name" in row.keys() else None,
        "type": row["type"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "days": row["days"],
        "status": row["status"],
        "notes": row["notes"],
        "decided_by": row["decided_by"],
        "decided_at": row["decided_at"],
        "created_at": row["created_at"],
    }


@bp.get("")
@require_auth
def list_leave():
    db = get_db()
    query = """SELECT lr.*, u.name AS user_name FROM leave_requests lr
               JOIN users u ON u.id = lr.user_id WHERE 1=1"""
    params = []

    if g.current_user["role"] == "admin":
        user_id = request.args.get("user_id")
        if user_id:
            query += " AND lr.user_id = ?"
            params.append(user_id)
    else:
        query += " AND lr.user_id = ?"
        params.append(g.current_user["id"])

    status = request.args.get("status")
    if status:
        query += " AND lr.status = ?"
        params.append(status)

    leave_type = request.args.get("type")
    if leave_type:
        query += " AND lr.type = ?"
        params.append(leave_type)

    query += " ORDER BY lr.start_date DESC"
    rows = db.execute(query, params).fetchall()
    return jsonify({"leave": [serialize_leave(r) for r in rows]})


@bp.post("")
@require_auth
def create_leave():
    data = request.get_json(silent=True) or {}
    leave_type = data.get("type")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    notes = (data.get("notes") or "").strip() or None

    if leave_type not in ("holiday", "sickness"):
        return jsonify({"error": "type must be 'holiday' or 'sickness'"}), 400
    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400

    try:
        d0 = parse_date(start_date)
        d1 = parse_date(end_date)
    except ValueError:
        return jsonify({"error": "dates must be in YYYY-MM-DD format"}), 400

    if d1 < d0:
        return jsonify({"error": "end_date must not be before start_date"}), 400
    if d0.year != d1.year:
        return jsonify({"error": "requests spanning a calendar year boundary must be split into two"}), 400

    # Admins may book leave for another employee by passing user_id; employees always book for themselves.
    target_user_id = g.current_user["id"]
    if g.current_user["role"] == "admin" and data.get("user_id"):
        target_user_id = data["user_id"]

    days = count_business_days(start_date, end_date)
    if days == 0:
        return jsonify({"error": "the selected range contains no weekdays"}), 400

    status = "approved" if leave_type == "sickness" else "pending"
    db = get_db()

    target_user = db.execute("SELECT * FROM users WHERE id = ? AND active = 1", (target_user_id,)).fetchone()
    if not target_user:
        return jsonify({"error": "target user not found"}), 404

    decided_fields = ""
    decided_values = []
    if status == "approved":
        decided_fields = ", decided_by, decided_at"
        decided_values = [g.current_user["id"], datetime.utcnow().isoformat()]

    new_id = insert_returning_id(
        db,
        f"""INSERT INTO leave_requests
            (user_id, type, start_date, end_date, days, status, notes{decided_fields})
            VALUES (?, ?, ?, ?, ?, ?, ?{',?' * len(decided_values)})""",
        [target_user_id, leave_type, start_date, end_date, days, status, notes] + decided_values,
    )
    db.commit()

    row = db.execute(
        """SELECT lr.*, u.name AS user_name FROM leave_requests lr
           JOIN users u ON u.id = lr.user_id WHERE lr.id = ?""",
        (new_id,),
    ).fetchone()

    result = serialize_leave(row)
    if leave_type == "holiday":
        result["balance_after_pending"] = compute_holiday_balance(db, target_user)
    return jsonify({"leave": result}), 201


@bp.patch("/<int:leave_id>")
@require_auth
@require_role("admin")
def update_leave(leave_id):
    """Lets an admin correct a leave record's dates/notes, regardless of its
    current status (e.g. fixing a mistake in an already-approved entry)."""
    db = get_db()
    row = db.execute("SELECT * FROM leave_requests WHERE id = ?", (leave_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    start_date = data.get("start_date", row["start_date"])
    end_date = data.get("end_date", row["end_date"])
    notes = data.get("notes", row["notes"])
    if isinstance(notes, str):
        notes = notes.strip() or None

    try:
        d0 = parse_date(start_date)
        d1 = parse_date(end_date)
    except ValueError:
        return jsonify({"error": "dates must be in YYYY-MM-DD format"}), 400
    if d1 < d0:
        return jsonify({"error": "end_date must not be before start_date"}), 400
    if d0.year != d1.year:
        return jsonify({"error": "requests spanning a calendar year boundary must be split into two"}), 400

    days = count_business_days(start_date, end_date)
    if days == 0:
        return jsonify({"error": "the selected range contains no weekdays"}), 400

    db.execute(
        "UPDATE leave_requests SET start_date = ?, end_date = ?, days = ?, notes = ? WHERE id = ?",
        (start_date, end_date, days, notes, leave_id),
    )
    db.commit()

    row = db.execute(
        """SELECT lr.*, u.name AS user_name FROM leave_requests lr
           JOIN users u ON u.id = lr.user_id WHERE lr.id = ?""",
        (leave_id,),
    ).fetchone()
    return jsonify({"leave": serialize_leave(row)})


@bp.patch("/<int:leave_id>/status")
@require_auth
@require_role("admin")
def update_status(leave_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("approved", "rejected"):
        return jsonify({"error": "status must be 'approved' or 'rejected'"}), 400

    db = get_db()
    row = db.execute("SELECT * FROM leave_requests WHERE id = ?", (leave_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    if row["status"] != "pending":
        return jsonify({"error": "only pending requests can be decided"}), 400

    db.execute(
        "UPDATE leave_requests SET status = ?, decided_by = ?, decided_at = ? WHERE id = ?",
        (new_status, g.current_user["id"], datetime.utcnow().isoformat(), leave_id),
    )
    db.commit()

    row = db.execute(
        """SELECT lr.*, u.name AS user_name FROM leave_requests lr
           JOIN users u ON u.id = lr.user_id WHERE lr.id = ?""",
        (leave_id,),
    ).fetchone()
    return jsonify({"leave": serialize_leave(row)})


@bp.delete("/<int:leave_id>")
@require_auth
def cancel_leave(leave_id):
    db = get_db()
    row = db.execute("SELECT * FROM leave_requests WHERE id = ?", (leave_id,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    is_owner = row["user_id"] == g.current_user["id"]
    is_admin = g.current_user["role"] == "admin"
    if not is_admin and not is_owner:
        return jsonify({"error": "Forbidden"}), 403
    if not is_admin and row["status"] != "pending":
        return jsonify({"error": "only pending requests can be cancelled"}), 400

    db.execute("DELETE FROM leave_requests WHERE id = ?", (leave_id,))
    db.commit()
    return jsonify({"ok": True})
