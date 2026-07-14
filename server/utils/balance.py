from datetime import date

from .dates import days_ago_iso


def get_org_settings(db):
    row = db.execute("SELECT * FROM org_settings WHERE id = 1").fetchone()
    return dict(row)


def compute_holiday_balance(db, user):
    """Running holiday balance for the current calendar year."""
    year = str(date.today().year)
    approved_used = db.execute(
        """SELECT COALESCE(SUM(days), 0) AS total FROM leave_requests
           WHERE user_id = ? AND type = 'holiday' AND status = 'approved'
             AND substr(start_date, 1, 4) = ?""",
        (user["id"], year),
    ).fetchone()["total"]

    pending_total = db.execute(
        """SELECT COALESCE(SUM(days), 0) AS total FROM leave_requests
           WHERE user_id = ? AND type = 'holiday' AND status = 'pending'
             AND substr(start_date, 1, 4) = ?""",
        (user["id"], year),
    ).fetchone()["total"]

    allowance = user["holiday_allowance_days"]
    remaining = allowance - approved_used
    projected_remaining = remaining - pending_total

    return {
        "year": int(year),
        "allowance_days": allowance,
        "approved_used_days": approved_used,
        "pending_days": pending_total,
        "remaining_days": remaining,
        "projected_remaining_days": projected_remaining,
        "over_limit": remaining < 0,
        "would_exceed_if_pending_approved": projected_remaining < 0,
    }


def compute_sickness_status(db, user):
    """Rolling 12-month sickness usage vs. threshold (per-employee override or org default)."""
    org = get_org_settings(db)
    threshold_days = user["sickness_alert_days"] if user["sickness_alert_days"] is not None else org["sickness_alert_days"]
    threshold_occurrences = (
        user["sickness_alert_occurrences"]
        if user["sickness_alert_occurrences"] is not None
        else org["sickness_alert_occurrences"]
    )

    window_start = days_ago_iso(365)

    row = db.execute(
        """SELECT COALESCE(SUM(days), 0) AS total_days, COUNT(*) AS occurrences
           FROM leave_requests
           WHERE user_id = ? AND type = 'sickness' AND status = 'approved'
             AND start_date >= ?""",
        (user["id"], window_start),
    ).fetchone()

    rolling_days = row["total_days"]
    rolling_occurrences = row["occurrences"]
    flagged = rolling_days > threshold_days or rolling_occurrences > threshold_occurrences

    return {
        "rolling_window_days": 365,
        "rolling_sick_days": rolling_days,
        "rolling_occurrences": rolling_occurrences,
        "threshold_days": threshold_days,
        "threshold_occurrences": threshold_occurrences,
        "flagged": flagged,
    }


def compute_full_balance(db, user):
    return {
        "user_id": user["id"],
        "name": user["name"],
        "holiday": compute_holiday_balance(db, user),
        "sickness": compute_sickness_status(db, user),
    }
