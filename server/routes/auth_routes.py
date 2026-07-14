from flask import Blueprint, request, jsonify, g

from ..db import get_db
from ..auth import verify_password, hash_password, create_token, require_auth

bp = Blueprint("auth_routes", __name__, url_prefix="/api/auth")


def serialize_user(user):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "holiday_allowance_days": user["holiday_allowance_days"],
        "sickness_alert_days": user["sickness_alert_days"],
        "sickness_alert_occurrences": user["sickness_alert_occurrences"],
        "start_date": user["start_date"],
        "active": bool(user["active"]),
    }


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ? AND active = 1", (email,)).fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user)
    return jsonify({"token": token, "user": serialize_user(user)})


@bp.get("/me")
@require_auth
def me():
    return jsonify({"user": serialize_user(g.current_user)})


@bp.patch("/password")
@require_auth
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "new password must be at least 8 characters"}), 400
    if not verify_password(current_password, g.current_user["password_hash"]):
        return jsonify({"error": "current password is incorrect"}), 401

    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(new_password), g.current_user["id"]),
    )
    db.commit()
    return jsonify({"ok": True})
