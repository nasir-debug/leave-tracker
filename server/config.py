import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

IS_PRODUCTION = os.environ.get("LEAVE_TRACKER_ENV") == "production"

# If DATABASE_URL is set (a Postgres connection string, e.g. from Neon/Supabase/
# Render Postgres), that's used as the datastore. Otherwise falls back to a local
# SQLite file, which is what local dev uses since this machine has no Postgres.
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

# Only relevant for the SQLite fallback. On Render's paid plans with a persistent
# disk, set LEAVE_TRACKER_DB_PATH to a file under the disk's mount path so data
# survives deploys/restarts.
DB_PATH = os.environ.get("LEAVE_TRACKER_DB_PATH", os.path.join(BASE_DIR, "data", "tracker.db"))

JWT_SECRET = os.environ.get("LEAVE_TRACKER_JWT_SECRET")
if not JWT_SECRET:
    if IS_PRODUCTION:
        raise RuntimeError(
            "LEAVE_TRACKER_JWT_SECRET must be set in production (generate one with "
            "`python3 -c \"import secrets; print(secrets.token_urlsafe(48))\"`)"
        )
    JWT_SECRET = "dev-secret-change-me-please-32-bytes-min"

JWT_ALGO = "HS256"
JWT_EXPIRY_HOURS = 24 * 7

# If set (and no users exist yet), a first admin account is created on startup
# so a fresh deploy has a working login without needing shell access.
BOOTSTRAP_ADMIN_EMAIL = os.environ.get("LEAVE_TRACKER_ADMIN_EMAIL")
BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("LEAVE_TRACKER_ADMIN_PASSWORD")
BOOTSTRAP_ADMIN_NAME = os.environ.get("LEAVE_TRACKER_ADMIN_NAME", "Admin")

# Org-wide sickness alert defaults (can be overridden in org_settings table / per-employee)
DEFAULT_HOLIDAY_ALLOWANCE_DAYS = 25
DEFAULT_CARRY_OVER_DAYS = 0
DEFAULT_SICKNESS_ALERT_DAYS = 10          # rolling 12-month sick days threshold
DEFAULT_SICKNESS_ALERT_OCCURRENCES = 3    # rolling 12-month separate episodes threshold
