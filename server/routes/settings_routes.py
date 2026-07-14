from flask import Blueprint, request, jsonify

from ..db import get_db
from ..auth import require_auth, require_role

bp = Blueprint("settings_routes", __name__, url_prefix="/api/settings")


@bp.get("")
@require_auth
@require_role("admin")
def get_settings():
    db = get_db()
    row = db.execute("SELECT * FROM org_settings WHERE id = 1").fetchone()
    return jsonify({"settings": dict(row)})


@bp.patch("")
@require_auth
@require_role("admin")
def update_settings():
    data = request.get_json(silent=True) or {}
    fields = []
    values = []

    for key in (
        "default_holiday_allowance_days",
        "sickness_alert_days",
        "sickness_alert_occurrences",
    ):
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])

    db = get_db()
    if fields:
        db.execute(f"UPDATE org_settings SET {', '.join(fields)} WHERE id = 1", values)
        db.commit()

    row = db.execute("SELECT * FROM org_settings WHERE id = 1").fetchone()
    return jsonify({"settings": dict(row)})
