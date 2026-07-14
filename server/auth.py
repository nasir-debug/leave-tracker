import datetime
from functools import wraps

import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from . import config
from .db import get_db


def hash_password(password):
    # Explicit method: this machine's Python build lacks hashlib.scrypt,
    # which is werkzeug's newer default.
    return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


def create_token(user):
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=config.JWT_EXPIRY_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGO)


def decode_token(token):
    return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGO])


def _get_token_from_request():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):]
    return None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE id = ? AND active = 1", (int(payload["sub"]),)
        ).fetchone()
        if not user:
            return jsonify({"error": "User not found or inactive"}), 401

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.current_user["role"] not in roles:
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
