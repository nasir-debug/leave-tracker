from flask import Blueprint, request, jsonify, g

from ..db import get_db, insert_returning_id
from ..auth import require_auth, require_role, hash_password
from ..utils.balance import compute_full_balance
from .auth_routes import serialize_user

bp = Blueprint("employee_routes", __name__, url_prefix="/api")


def _validate_employee_payload(data, require_password):
    errors = []
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    role = data.get("role", "employee")
    start_date = data.get("start_date")
    holiday_allowance_days = data.get("holiday_allowance_days", 25)
    carry_over_days = data.get("carry_over_days", 0)

    if not name:
        errors.append("name is required")
    if not email or "@" not in email:
        errors.append("a valid email is required")
    if role not in ("admin", "employee"):
        errors.append("role must be 'admin' or 'employee'")
    if not start_date:
        errors.append("start_date is required")
    try:
        holiday_allowance_days = float(holiday_allowance_days)
        if holiday_allowance_days < 0:
            errors.append("holiday_allowance_days must be >= 0")
    except (TypeError, ValueError):
        errors.append("holiday_allowance_days must be a number")
    try:
        carry_over_days = float(carry_over_days)
    except (TypeError, ValueError):
        errors.append("carry_over_days must be a number")
    if require_password and not data.get("password"):
        errors.append("password is required")

    return errors, {
        "name": name,
        "email": email,
        "role": role,
        "start_date": start_date,
        "holiday_allowance_days": holiday_allowance_days,
        "carry_over_days": carry_over_days,
        "sickness_alert_days": data.get("sickness_alert_days"),
        "sickness_alert_occurrences": data.get("sickness_alert_occurrences"),
    }


@bp.get("/employees")
@require_auth
@require_role("admin")
def list_employees():
    db = get_db()
    users = db.execute("SELECT * FROM users WHERE active = 1 ORDER BY name").fetchall()
    result = []
    for u in users:
        entry = serialize_user(u)
        entry["balance"] = compute_full_balance(db, u)
        result.append(entry)
    return jsonify({"employees": result})


@bp.get("/employees/<int:user_id>")
@require_auth
def get_employee(user_id):
    if g.current_user["role"] != "admin" and g.current_user["id"] != user_id:
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "Not found"}), 404
    entry = serialize_user(user)
    entry["balance"] = compute_full_balance(db, user)
    return jsonify({"employee": entry})


@bp.post("/employees")
@require_auth
@require_role("admin")
def create_employee():
    data = request.get_json(silent=True) or {}
    errors, clean = _validate_employee_payload(data, require_password=True)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (clean["email"],)).fetchone()
    if existing:
        return jsonify({"error": "A user with that email already exists"}), 409

    new_id = insert_returning_id(
        db,
        """INSERT INTO users
           (name, email, password_hash, role, holiday_allowance_days, carry_over_days,
            sickness_alert_days, sickness_alert_occurrences, start_date, active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            clean["name"],
            clean["email"],
            hash_password(data.get("password")),
            clean["role"],
            clean["holiday_allowance_days"],
            clean["carry_over_days"],
            clean["sickness_alert_days"],
            clean["sickness_alert_occurrences"],
            clean["start_date"],
        ),
    )
    db.commit()
    user = db.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
    entry = serialize_user(user)
    entry["balance"] = compute_full_balance(db, user)
    return jsonify({"employee": entry}), 201


@bp.patch("/employees/<int:user_id>")
@require_auth
@require_role("admin")
def update_employee(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    fields = []
    values = []

    if "name" in data:
        fields.append("name = ?")
        values.append((data.get("name") or "").strip())
    if "email" in data:
        email = (data.get("email") or "").strip().lower()
        if "@" not in email:
            return jsonify({"error": "a valid email is required"}), 400
        fields.append("email = ?")
        values.append(email)
    if "role" in data:
        if data["role"] not in ("admin", "employee"):
            return jsonify({"error": "role must be 'admin' or 'employee'"}), 400
        fields.append("role = ?")
        values.append(data["role"])
    if "holiday_allowance_days" in data:
        try:
            fields.append("holiday_allowance_days = ?")
            values.append(float(data["holiday_allowance_days"]))
        except (TypeError, ValueError):
            return jsonify({"error": "holiday_allowance_days must be a number"}), 400
    if "carry_over_days" in data:
        try:
            fields.append("carry_over_days = ?")
            values.append(float(data["carry_over_days"]))
        except (TypeError, ValueError):
            return jsonify({"error": "carry_over_days must be a number"}), 400
    if "sickness_alert_days" in data:
        fields.append("sickness_alert_days = ?")
        values.append(data["sickness_alert_days"])
    if "sickness_alert_occurrences" in data:
        fields.append("sickness_alert_occurrences = ?")
        values.append(data["sickness_alert_occurrences"])
    if "start_date" in data:
        fields.append("start_date = ?")
        values.append(data["start_date"])
    if "password" in data and data["password"]:
        fields.append("password_hash = ?")
        values.append(hash_password(data["password"]))

    if fields:
        values.append(user_id)
        db.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()

    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    entry = serialize_user(user)
    entry["balance"] = compute_full_balance(db, user)
    return jsonify({"employee": entry})


@bp.delete("/employees/<int:user_id>")
@require_auth
@require_role("admin")
def deactivate_employee(user_id):
    if g.current_user["id"] == user_id:
        return jsonify({"error": "You cannot deactivate your own account"}), 400
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "Not found"}), 404
    db.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({"ok": True})


@bp.get("/balance/me")
@require_auth
def my_balance():
    db = get_db()
    return jsonify({"balance": compute_full_balance(db, g.current_user)})
