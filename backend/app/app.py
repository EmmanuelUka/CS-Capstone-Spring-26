import hashlib
import hmac
import logging
import os
import secrets
import sys
import uuid
from dataclasses import asdict
from datetime import timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlencode, urlparse

import msal
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))

import eval_utility_flask as eval_api
import hashmark_db as recruiting_db
import playerEval as pe
import player_metrics
from db import (
    attach_subject_to_user,
    delete_user,
    get_user_by_email,
    get_user_by_subject,
    get_user_list,
    init_db as init_auth_db,
    sync_super_admins,
    update_user_role,
    upsert_user,
)


# =========================================================
# Environment / Startup
# =========================================================

# Loads variables from the .env file into the environment so the app can read
# config like secrets, URLs, etc.
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    # Small helper to convert env values like "true", "1", "yes", etc. into
    # actual booleans.
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str) -> list[str]:
    # Reads a comma-separated env var and turns it into a list.
    # Example: "a@test.com,b@test.com" -> ["a@test.com", "b@test.com"]
    raw = os.getenv(name, "") or ""
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


# =========================================================
# Logging
# =========================================================

def _setup_logging():
    # Reads logging config from env and sets up console/file logging.
    # This is meant to make logging easy to control without changing code.
    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Prevent logging from being configured multiple times if the module gets
    # imported more than once.
    if getattr(root, "_hashmark_logging_configured", False):
        return
    root._hashmark_logging_configured = True

    fmt = os.getenv("LOG_FORMAT") or "%(asctime)s | %(levelname)s | %(message)s"
    formatter = logging.Formatter(fmt)

    # Console logging for local dev / terminal visibility.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # Optional rotating file logging if LOG_FILE is set.
    log_file = (os.getenv("LOG_FILE") or "").strip()
    if log_file:
        parent = os.path.dirname(log_file)
        if parent:
            os.makedirs(parent, exist_ok=True)

        max_bytes = int(os.getenv("LOG_FILE_MAX_BYTES") or str(10 * 1024 * 1024))
        backups = int(os.getenv("LOG_FILE_BACKUP_COUNT") or "5")

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backups,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def _sanitize_log_value(value) -> str:
    # Converts values to strings and truncates very long values.
    if value is None:
        return ""

    s = str(value)
    if len(s) > 500:
        s = s[:500] + "...(truncated)"
    return s


def _log_secret() -> bytes:
    # Separate secret used only for pseudonymous log identifiers.
    value = (os.getenv("LOG_PSEUDO_KEY") or "").strip()
    if not value:
        raise RuntimeError("LOG_PSEUDO_KEY must be set")
    return value.encode("utf-8")


def _log_pseudo(value: str | None) -> str:
    # Deterministic pseudonymous ID for logs. Same input -> same output.
    if not value:
        return ""
    normalized = value.strip().lower().encode("utf-8")
    digest = hmac.new(_log_secret(), normalized, hashlib.sha256).hexdigest()
    return digest[:16]


def _mask_email(email: str | None) -> str:
    # Human-readable masked email for optional log readability.
    if not email:
        return ""

    email = email.strip().lower()
    if "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + ("*" * (len(local) - 2)) + local[-1]

    return f"{masked_local}@{domain}"


def _log_identity_fields(prefix: str, email: str | None = None) -> dict[str, str]:
    # Returns safe log fields for an email-based identity.
    fields = {}
    if email:
        fields[f"{prefix}_id"] = _log_pseudo(email)

        if _env_bool("LOG_INCLUDE_MASKED_EMAILS", default=True):
            fields[f"{prefix}_masked"] = _mask_email(email)

    return fields


def _log_subject_fields(subject: str | None) -> dict[str, str]:
    # Returns safe log fields for provider subject values.
    if not subject:
        return {}
    return {"subject_id": _log_pseudo(subject)}


def _log_event(event: str, level: str = "INFO", **fields):
    # General structured logging helper.
    # Everything gets logged as key=value pairs so logs are easier to scan.
    parts = [f"event={_sanitize_log_value(event)}"]
    for key, value in fields.items():
        if value is None:
            continue
        parts.append(f"{key}={_sanitize_log_value(value)}")

    msg = " ".join(parts)
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.log(lvl, msg)


# =========================================================
# Request / Security Helpers
# =========================================================

def _get_request_id():
    # Try to reuse an incoming request/correlation ID if one exists.
    # If not, make a new one for tracing this request through logs.
    rid = request.headers.get("X-Request-Id") or request.headers.get(
        "X-Correlation-Id"
    )
    return rid or str(uuid.uuid4())


def _redirect_frontend_error(code: str):
    # Redirect the user back to the frontend with an auth error code so the UI
    # can display the correct message.
    query = urlencode({"auth_error": code})
    return redirect(f"{_get_frontend_redirect_base()}/?{query}")


def _is_allowed_frontend_origin(candidate: str) -> bool:
    # Restrict callback redirect targets to configured frontend origins.
    if not candidate:
        return False

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return origin in API_ORIGINS or origin == FRONTEND_URL


def _get_frontend_redirect_base() -> str:
    # Use a validated per-login return target when present, otherwise fall back
    # to the configured default frontend URL.
    candidate = (session.get("frontend_return_to") or "").rstrip("/")
    return candidate if _is_allowed_frontend_origin(candidate) else FRONTEND_URL


def _email_domain_allowed(email: str) -> bool:
    # If allowed domains are configured, the email must belong to one of them.
    # If no domains are configured, all domains are allowed.
    email = (email or "").lower()
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1]
    return (not ALLOWED_EMAIL_DOMAINS) or (domain in ALLOWED_EMAIL_DOMAINS)


def _is_super_admin_email(email: str) -> bool:
    # Checks whether this email is one of the super admins defined in the
    # environment config.
    return (email or "").strip().lower() in SUPER_ADMIN_EMAILS


def _ensure_csrf_token() -> str:
    # Makes sure the current session has a CSRF token.
    # If not, create one and store it in the session.
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _require_csrf():
    # Enforce CSRF validation on state-changing requests.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        sent = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")

        if not expected or not sent or sent != expected:
            rid = request.environ.get("request_id")
            ip = request.remote_addr
            _log_event(
                "csrf_failed",
                level="WARNING",
                ip=ip,
                endpoint=request.path,
                method=request.method,
                request_id=rid,
            )
            return jsonify({"error": "csrf_failed"}), 403

    return None


def require_role(*roles):
    # Decorator for routes that require the user to be logged in and have one of
    # the allowed roles.
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                rid = request.environ.get("request_id")
                ip = request.remote_addr
                _log_event(
                    "not_authenticated",
                    level="WARNING",
                    ip=ip,
                    endpoint=request.path,
                    method=request.method,
                    request_id=rid,
                )
                return jsonify({"error": "not_authenticated"}), 401

            if user.get("role") not in roles:
                rid = request.environ.get("request_id")
                ip = request.remote_addr
                _log_event(
                    "forbidden",
                    level="WARNING",
                    ip=ip,
                    endpoint=request.path,
                    method=request.method,
                    request_id=rid,
                    required=",".join(roles),
                    role=user.get("role"),
                )
                return jsonify({"error": "forbidden", "required": roles}), 403

            return fn(*args, **kwargs)

        return wrapper

    return deco


# =========================================================
# Flask App / Core Configuration
# =========================================================

app = Flask(__name__)
_setup_logging()
logging.getLogger("werkzeug").disabled = False  # Change to True to clean up logs

# App environment controls things like production defaults.
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PROD = APP_ENV == "production"

# Flask session secret key. (must exist or the app should not start)
secret = os.getenv("FLASK_SECRET_KEY")
if not secret:
    raise RuntimeError("FLASK_SECRET_KEY must be set")
app.secret_key = secret

# Frontend URL is used for redirects after login/callback.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

# Allowed CORS origins for frontend requests.
API_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",")
    if origin.strip()
]

# In production, require real CORS origins and do not allow wildcard because
# credentials/cookies are being used.
if IS_PROD:
    if not API_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must be set in production")
    if any(origin == "*" for origin in API_ORIGINS):
        raise RuntimeError(
            "CORS_ORIGINS cannot include '*' when supports_credentials=True"
        )

# If running behind a reverse proxy, ProxyFix helps Flask trust forwarded
# headers like real IP / protocol.
if _env_bool("USE_PROXY_FIX", default=IS_PROD):
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=int(os.getenv("PROXY_FIX_X_FOR", "1")),
        x_proto=int(os.getenv("PROXY_FIX_X_PROTO", "1")),
        x_host=int(os.getenv("PROXY_FIX_X_HOST", "1")),
        x_port=int(os.getenv("PROXY_FIX_X_PORT", "0")),
    )

cookie_secure = _env_bool("COOKIE_SECURE", default=IS_PROD)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  # Prevent JS from reading the session cookie.
    SESSION_COOKIE_SAMESITE=os.getenv(
        "SESSION_SAMESITE", "Lax"
    ),  # Controls cross-site cookie behavior.
    SESSION_COOKIE_SECURE=cookie_secure,  # Secure cookies only over HTTPS.
    PERMANENT_SESSION_LIFETIME=timedelta(  # Session expiration window.
        hours=int(os.getenv("SESSION_HOURS", "8"))
    ),
)

# Enable CORS for the allowed frontend origins.
CORS(app, supports_credentials=True, origins=API_ORIGINS)

# Use stricter CSP in production and a more relaxed one in development.
if IS_PROD:
    talisman_csp = {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
        ],
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",
        ],
        "script-src": ["'self'"],
        "connect-src": ["'self'"] + API_ORIGINS,
        "base-uri": ["'self'"],
        "frame-ancestors": ["'none'"],
        "object-src": ["'none'"],
    }
else:
    talisman_csp = {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "style-src": ["'self'", "'unsafe-inline'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        "connect-src": ["'self'"] + API_ORIGINS,
    }

# Whether to force HTTPS redirects.
force_https = _env_bool("FORCE_HTTPS", default=False)
Talisman(app, content_security_policy=talisman_csp, force_https=force_https)

# Global rate limiter. Uses client IP as the key.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "300 per hour")],
)


# =========================================================
# Microsoft Auth Configuration
# =========================================================

CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
TENANT = os.getenv("MICROSOFT_TENANT", "common")
REDIRECT_URI = os.getenv(
    "MICROSOFT_REDIRECT_URI",
    "http://localhost:5000/auth/microsoft/callback",
)

# Optional email domain allowlist.
ALLOWED_EMAIL_DOMAINS = [
    domain.strip().lower()
    for domain in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",")
    if domain.strip()
]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"
SCOPES = ["User.Read"]

# Super admins managed from env.
SUPER_ADMIN_EMAILS = set(_env_list("SUPER_ADMIN_EMAILS"))
ENFORCE_SUPER_ADMIN_LIST = _env_bool("ENFORCE_SUPER_ADMIN_LIST", default=True)


def _build_msal_app():
    # Builds the MSAL confidential client used for Microsoft OAuth.
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "Missing MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET in .env"
        )

    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )


# =========================================================
# Database Startup
# =========================================================

init_auth_db()  # Create auth tables if needed.
recruiting_db.init_db()  # Create recruiting tables if needed.

# Sync env-defined super admins into the database.
sync_super_admins(SUPER_ADMIN_EMAILS, enforce=ENFORCE_SUPER_ADMIN_LIST)


# =========================================================
# Flask Hooks / Error Handlers
# =========================================================

@app.before_request
def _before_request():
    # Assign a request ID to every incoming request so logs can be traced
    # across the full lifecycle of the request.
    request.environ["request_id"] = _get_request_id()

    if request.path.startswith("/auth/microsoft/callback"):
        return None

    if request.path == "/health":
        return None

    if request.path.startswith("/auth/microsoft/login"):
        return None

    return _require_csrf()


@app.after_request
def _log_denials(resp):
    # Logs 401 and 403 responses after the request finishes.
    try:
        rid = request.environ.get("request_id")
        ip = request.remote_addr
        endpoint = request.path

        if resp.status_code in (401, 403):
            _log_event(
                "access_denied",
                level="WARNING",
                ip=ip,
                endpoint=endpoint,
                method=request.method,
                status=resp.status_code,
                request_id=rid,
            )
    except Exception:
        pass

    return resp


@app.errorhandler(RateLimitExceeded)
def _rate_limit_exceeded(e):
    # Handles Flask-Limiter exceptions in a consistent way.
    rid = request.environ.get("request_id")
    ip = request.remote_addr
    endpoint = request.path

    _log_event(
        "rate_limit_triggered",
        level="WARNING",
        ip=ip,
        endpoint=endpoint,
        method=request.method,
        request_id=rid,
        detail=getattr(e, "description", ""),
    )
    return jsonify({"error": "rate_limited"}), 429


# =========================================================
# Basic Routes
# =========================================================

@app.get("/health")
def health():
    # Simple health check route.
    return jsonify({"ok": True})


@app.get("/api/csrf")
def api_csrf():
    # Frontend can call this to get the current CSRF token.
    return jsonify({"csrfToken": _ensure_csrf_token()})


@app.post("/auth/logout")
@limiter.limit(os.getenv("RATE_LIMIT_LOGOUT", "30 per minute"))
def logout():
    # Clears the session and logs the user out.
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    # Returns the current logged-in user from session.
    # Also ensures a CSRF token exists for authenticated sessions.
    if session.get("user"):
        _ensure_csrf_token()
    return jsonify(session.get("user"))


# =========================================================
# Microsoft Authentication Routes
# =========================================================

@app.get("/auth/microsoft/login")
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "30 per minute"))
def microsoft_login():
    # Starts the Microsoft login flow.
    rid = request.environ.get("request_id")
    ip = request.remote_addr

    _log_event(
        "login_attempt",
        level="INFO",
        ip=ip,
        endpoint=request.path,
        method=request.method,
        request_id=rid,
    )

    # Clear any previous session before starting a fresh login flow.
    session.clear()
    session.permanent = True

    return_to = (request.args.get("return_to") or "").strip().rstrip("/")
    session["frontend_return_to"] = (
        return_to if _is_allowed_frontend_origin(return_to) else FRONTEND_URL
    )

    msal_app = _build_msal_app()
    state = str(uuid.uuid4())

    # Start Microsoft auth flow using PKCE.
    flow = msal_app.initiate_auth_code_flow(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state,
        prompt="select_account",
    )
    session["flow"] = flow
    return redirect(flow["auth_uri"])


@app.route("/auth/microsoft/callback", methods=["GET", "POST"])
@limiter.limit(os.getenv("RATE_LIMIT_CALLBACK", "60 per minute"))
def microsoft_callback():
    # Handles the Microsoft OAuth callback, validates the login, and creates the user session if access is authorized.
    rid = request.environ.get("request_id")
    ip = request.remote_addr

    callback_data = request.values

    _log_event(
        "oauth_callback_received",
        level="INFO",
        ip=ip,
        endpoint=request.path,
        method=request.method,
        request_id=rid,
        has_code=bool(callback_data.get("code")),
        has_state=bool(callback_data.get("state")),
        has_error=bool(callback_data.get("error")),
    )

    msal_app = _build_msal_app()

    flow = session.get("flow") or {}
    try:
        token = msal_app.acquire_token_by_auth_code_flow(flow, callback_data)
    except ValueError:
        _log_event(
            "oauth_callback_invalid_state",
            level="WARNING",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
        )
        return _redirect_frontend_error("invalid_state")

    session.pop("flow", None)

    # If token exchange failed, stop here.
    if "access_token" not in token:
        _log_event(
            "token_validation_failed",
            level="ERROR",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            msal_error=token.get("error"),
            msal_error_description=token.get("error_description"),
        )
        return _redirect_frontend_error("token_failed")

    access_token = token["access_token"]
    claims = token.get("id_token_claims") or {}
    tid = claims.get("tid") or "unknown"

    # Call Microsoft Graph to get the user's profile.
    try:
        me = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=(5, 30),
        )
    except requests.exceptions.Timeout:
        _log_event(
            "graph_timeout",
            level="ERROR",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
        )
        return _redirect_frontend_error("graph_timeout")
    except requests.exceptions.RequestException:
        _log_event(
            "graph_failed",
            level="ERROR",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
        )
        return _redirect_frontend_error("graph_failed")

    if me.status_code != 200:
        _log_event(
            "graph_failed",
            level="ERROR",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
        )
        return _redirect_frontend_error("graph_failed")

    profile = me.json()
    oid = profile.get("id")
    email = (profile.get("mail") or profile.get("userPrincipalName") or "").lower()
    name = profile.get("displayName") or ""

    # Must have an email to continue.
    if not email:
        _log_event(
            "profile_missing_email",
            level="WARNING",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
        )
        return redirect(_get_frontend_redirect_base() + "/?auth=denied")

    # Check if the email domain is allowed.
    if not _email_domain_allowed(email):
        _log_event(
            "domain_not_allowed",
            level="WARNING",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            **_log_identity_fields("user", email),
        )
        return _redirect_frontend_error("domain_not_allowed")

    # Build a stable subject string from tenant ID + object ID.
    subject = f"{tid}:{oid}" if tid and oid else None

    # Make sure authenticated sessions have CSRF token ready.
    _ensure_csrf_token()

    # If this email is configured as super admin in env, force it into the DB
    # and session as SUPER_ADMIN.
    if _is_super_admin_email(email):
        upsert_user(email=email, role="SUPER_ADMIN", provider_subject=subject)
        session["user"] = {
            "email": email,
            "role": "SUPER_ADMIN",
            "name": name,
            "subject": subject,
        }
        _log_event(
            "login_success",
            level="INFO",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            role="SUPER_ADMIN",
            method="super_admin_env",
            **_log_identity_fields("user", email),
            **_log_subject_fields(subject),
        )
        return redirect(_get_frontend_redirect_base() + "/")

    # First try matching on provider subject if available.
    if subject:
        user = get_user_by_subject(subject)
        if user:
            session["user"] = {
                "email": email,
                "role": user["role"],
                "name": name,
                "subject": subject,
            }
            _log_event(
                "login_success",
                level="INFO",
                ip=ip,
                endpoint=request.path,
                request_id=rid,
                role=user["role"],
                method="subject_match",
                **_log_identity_fields("user", email),
                **_log_subject_fields(subject),
            )
            return redirect(_get_frontend_redirect_base() + "/")

    # If subject match did not work, fall back to email match.
    user = get_user_by_email(email)
    if user:
        # If this user existed before subject was known, bind the new provider
        # subject now.
        if subject and not user["provider_subject"]:
            attach_subject_to_user(email, subject)
            _log_event(
                "subject_bound",
                level="INFO",
                ip=ip,
                endpoint=request.path,
                request_id=rid,
                **_log_identity_fields("user", email),
                **_log_subject_fields(subject),
            )

        session["user"] = {
            "email": email,
            "role": user["role"],
            "name": name,
            "subject": subject,
        }
        _log_event(
            "login_success",
            level="INFO",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            role=user["role"],
            method="email_match",
            **_log_identity_fields("user", email),
            **_log_subject_fields(subject),
        )
        return redirect(_get_frontend_redirect_base() + "/")

    # If no matching approved user exists, deny access.
    _log_event(
        "access_not_granted",
        level="WARNING",
        ip=ip,
        endpoint=request.path,
        request_id=rid,
        **_log_identity_fields("user", email),
        **_log_subject_fields(subject),
    )
    return _redirect_frontend_error("access_not_granted")


# =========================================================
# User Management Routes
# =========================================================

@app.get("/api/users")
@require_role("SUPER_ADMIN", "ADMIN")
def api_users():
    # Returns the user list for admin views.
    return jsonify({"users": get_user_list()})


@app.post("/api/users")
@require_role("SUPER_ADMIN", "ADMIN")
@limiter.limit(os.getenv("RATE_LIMIT_ADD_USER", "20 per minute"))
def api_add_user():
    # Adds a new allowed user to the system.
    rid = request.environ.get("request_id")
    ip = request.remote_addr
    actor = session.get("user", {}).get("email")

    if not request.is_json:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="add_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="expected_json",
            **_log_identity_fields("actor", actor),
        )
        return jsonify({"error": "expected_json"}), 400

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "").strip().upper() or "COACH"

    if not email or "@" not in email:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="add_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="invalid_email",
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "invalid_email"}), 400

    if not _email_domain_allowed(email):
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="add_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="email_domain_not_allowed",
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "email_domain_not_allowed"}), 400

    # Regular admins are only allowed to add coaches.
    requester_role = session.get("user", {}).get("role")
    if requester_role == "ADMIN" and role != "COACH":
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="add_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="forbidden_role",
            role=role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "forbidden_role"}), 403

    # This route only allows creating ADMIN or COACH.
    if role not in {"ADMIN", "COACH"}:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="add_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="invalid_role",
            role=role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "invalid_role"}), 400

    existing = get_user_by_email(email)

    if existing:
        _log_event(
            "user_create_attempt_existing",
            level="INFO",
            role=role,
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"ok": True, "status": "user_exists"})

    upsert_user(email=email, role=role)

    _log_event(
        "user_created",
        level="INFO",
        action="add_user",
        role=role,
        ip=ip,
        endpoint=request.path,
        request_id=rid,
        **_log_identity_fields("actor", actor),
        **_log_identity_fields("target", email),
    )

    return jsonify({"ok": True, "status": "created"})


@app.patch("/api/users/role")
@require_role("SUPER_ADMIN")
@limiter.limit(os.getenv("RATE_LIMIT_SET_ROLE", "20 per minute"))
def api_set_user_role():
    # Lets only SUPER_ADMIN change user roles.
    rid = request.environ.get("request_id")
    ip = request.remote_addr
    actor = session.get("user", {}).get("email")

    if not request.is_json:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="set_user_role",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="expected_json",
            **_log_identity_fields("actor", actor),
        )
        return jsonify({"error": "expected_json"}), 400

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "").strip().upper()

    if not email or "@" not in email:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="set_user_role",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="invalid_email",
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "invalid_email"}), 400

    # SUPER_ADMIN cannot assign SUPER_ADMIN through this route.
    # This only supports ADMIN and COACH role changes.
    if role not in {"ADMIN", "COACH"}:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="set_user_role",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="invalid_role",
            new_role=role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "invalid_role"}), 400

    # Prevent self-demotion / self-change.
    if email == session["user"]["email"].lower():
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="set_user_role",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="cannot_modify_self",
            new_role=role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "cannot_modify_self"}), 403

    target = get_user_by_email(email)
    if not target:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="set_user_role",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="user_not_found",
            new_role=role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "user_not_found"}), 404

    # Do not allow this route to modify another super admin.
    if (target["role"] or "").upper() == "SUPER_ADMIN":
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="set_user_role",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="cannot_modify_super_admin",
            new_role=role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "cannot_modify_super_admin"}), 403

    update_user_role(email, role)

    _log_event(
        "user_role_changed",
        level="INFO",
        action="set_user_role",
        new_role=role,
        ip=ip,
        endpoint=request.path,
        request_id=rid,
        **_log_identity_fields("actor", actor),
        **_log_identity_fields("target", email),
    )

    return jsonify({"ok": True})


@app.delete("/api/users")
@require_role("SUPER_ADMIN", "ADMIN")
@limiter.limit(os.getenv("RATE_LIMIT_DELETE_USER", "20 per minute"))
def api_delete_user():
    # Deletes a user from the system entirely.
    rid = request.environ.get("request_id")
    ip = request.remote_addr
    actor = session.get("user", {}).get("email")

    if not request.is_json:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="delete_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="expected_json",
            **_log_identity_fields("actor", actor),
        )
        return jsonify({"error": "expected_json"}), 400

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email or "@" not in email:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="delete_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="invalid_email",
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "invalid_email"}), 400

    # Do not allow users to delete themselves.
    if email == session["user"]["email"].lower():
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="delete_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="cannot_modify_self",
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "cannot_modify_self"}), 403

    target = get_user_by_email(email)
    if not target:
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="delete_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="user_not_found",
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "user_not_found"}), 404

    target_role = (target["role"] or "").upper()
    requester_role = session["user"]["role"]

    # Nobody should delete a SUPER_ADMIN through this route.
    if target_role == "SUPER_ADMIN":
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="delete_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="cannot_modify_super_admin",
            target_role=target_role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "cannot_modify_super_admin"}), 403

    # Regular admins can only delete coaches.
    if requester_role == "ADMIN" and target_role != "COACH":
        _log_event(
            "admin_action_failed",
            level="WARNING",
            action="delete_user",
            ip=ip,
            endpoint=request.path,
            request_id=rid,
            reason="forbidden_target_role",
            target_role=target_role,
            **_log_identity_fields("actor", actor),
            **_log_identity_fields("target", email),
        )
        return jsonify({"error": "forbidden_target_role"}), 403

    _log_event(
        "user_deleted",
        level="INFO",
        action="delete_user",
        target_role=target_role,
        ip=ip,
        endpoint=request.path,
        request_id=rid,
        **_log_identity_fields("actor", actor),
        **_log_identity_fields("target", email),
    )

    delete_user(email)
    return jsonify({"ok": True})

# =========================================================
# Data Endpoints For The Frontend
# =========================================================

### End endpoint should check that the user has a valid session. Otherwise, prompt user to log in again

EXAMPLE_RECRUITING_PLAYERS = [
    {
        "id": 1,
        "name": "Evan Brooks",
        "school": "St. Xavier",
        "state": "OH",
        "city": "Cincinnati",
        "classYear": 2027,
        "position": "QB",
        "projectedPosition": "RPO Quarterback",
        "type": "High School",
        "height": "6'2\"",
        "weight": 204,
        "fortyTime": "4.68",
        "gpa": 3.7,
        "rating": 91,
        "stars": 4,
        "jersey": "#7",
        "archetype": "Field Commander",
        "summary": "Quick processor with strong middle-of-field accuracy and enough mobility to keep zone-read tags live.",
        "explanation": "Best fit in a spread system that wants early-decision throws, designed movement, and efficient third-down answers.",
        "notes": "High-volume thrower with clean mechanics. Coaches flagged leadership and poise as early separators.",
        "schemeFit": 93,
        "comparisonScore": 92,
        "confidenceScore": 88,
        "breakdown": {"physical": 82, "athletic": 79, "production": 94, "context": 87},
        "stats": {"passingYards": 3248, "touchdowns": 34, "interceptions": 6, "rushYards": 512},
        "topComparables": [4, 6, 7],
    },
    {
        "id": 2,
        "name": "Malik Dorsey",
        "school": "Buford",
        "state": "GA",
        "city": "Buford",
        "classYear": 2027,
        "position": "WR",
        "projectedPosition": "Boundary X Receiver",
        "type": "High School",
        "height": "6'3\"",
        "weight": 196,
        "fortyTime": "4.43",
        "gpa": 3.4,
        "rating": 94,
        "stars": 4,
        "jersey": "#1",
        "archetype": "Vertical Winner",
        "summary": "Explosive outside target who wins stacked releases, tracks the deep ball, and creates red-zone leverage.",
        "explanation": "Prototype boundary receiver for an offense that wants isolated shot plays and a back-shoulder answer on money downs.",
        "notes": "Elite acceleration off the line. Needs more polish on underneath pacing but already changes coverage structure.",
        "schemeFit": 95,
        "comparisonScore": 94,
        "confidenceScore": 90,
        "breakdown": {"physical": 86, "athletic": 94, "production": 89, "context": 85},
        "stats": {"receptions": 71, "receivingYards": 1284, "touchdowns": 16, "contestedCatchRate": "68%"},
        "topComparables": [5, 6, 4],
    },
    {
        "id": 3,
        "name": "Isaiah Ford",
        "school": "IMG Academy",
        "state": "FL",
        "city": "Bradenton",
        "classYear": 2027,
        "position": "LB",
        "projectedPosition": "Run-and-Chase Mike",
        "type": "High School",
        "height": "6'1\"",
        "weight": 228,
        "fortyTime": "4.59",
        "gpa": 3.6,
        "rating": 89,
        "stars": 3,
        "jersey": "#32",
        "archetype": "Front-Seven Eraser",
        "summary": "Trigger-fast second-level defender with strong pursuit angles and reliable finish technique.",
        "explanation": "Profiles as a middle linebacker in pressure packages where range and closing speed matter more than pure size.",
        "notes": "Very clean diagnostic tape. One of the safest defensive evaluations in the board.",
        "schemeFit": 91,
        "comparisonScore": 90,
        "confidenceScore": 92,
        "breakdown": {"physical": 81, "athletic": 90, "production": 88, "context": 89},
        "stats": {"tackles": 117, "tacklesForLoss": 18, "sacks": 6, "forcedFumbles": 3},
        "topComparables": [7, 5, 1],
    },
    {
        "id": 4,
        "name": "Tyler Morris",
        "school": "North Shore",
        "state": "TX",
        "city": "Houston",
        "classYear": 2026,
        "position": "QB",
        "projectedPosition": "Pocket Distributor",
        "type": "Transfer",
        "height": "6'4\"",
        "weight": 212,
        "fortyTime": "4.84",
        "gpa": 3.8,
        "rating": 87,
        "stars": 3,
        "jersey": "#12",
        "archetype": "Timing Thrower",
        "summary": "Tall pocket passer with advanced anticipation and clean footwork in structured dropback concepts.",
        "explanation": "Best fit in a timing-based offense that majors in play-action, deeper dig windows, and controlled movement.",
        "notes": "Less dynamic outside structure, but the floor is high because of processing and touch.",
        "schemeFit": 88,
        "comparisonScore": 86,
        "confidenceScore": 84,
        "breakdown": {"physical": 84, "athletic": 71, "production": 85, "context": 88},
        "stats": {"passingYards": 2987, "touchdowns": 27, "interceptions": 8, "completionRate": "68%"},
        "topComparables": [1, 6, 7],
    },
    {
        "id": 5,
        "name": "Jalen Strickland",
        "school": "Cass Tech",
        "state": "MI",
        "city": "Detroit",
        "classYear": 2026,
        "position": "CB",
        "projectedPosition": "Press Corner",
        "type": "High School",
        "height": "6'0\"",
        "weight": 184,
        "fortyTime": "4.41",
        "gpa": 3.5,
        "rating": 90,
        "stars": 4,
        "jersey": "#4",
        "archetype": "Mirror Corner",
        "summary": "Length, patience, and recovery burst show up immediately against high-level wideouts.",
        "explanation": "Strong match for a defense that wants man coverage flexibility and trusts corners to challenge the release.",
        "notes": "Ball production climbed late. Still adding lower-body power but the coverage traits are real.",
        "schemeFit": 92,
        "comparisonScore": 89,
        "confidenceScore": 87,
        "breakdown": {"physical": 80, "athletic": 93, "production": 84, "context": 86},
        "stats": {"passBreakups": 14, "interceptions": 5, "tackles": 39, "completionAllowed": "38%"},
        "topComparables": [2, 3, 7],
    },
    {
        "id": 6,
        "name": "Caden Price",
        "school": "Bishop Gorman",
        "state": "NV",
        "city": "Las Vegas",
        "classYear": 2027,
        "position": "TE",
        "projectedPosition": "Move Tight End",
        "type": "Transfer",
        "height": "6'5\"",
        "weight": 232,
        "fortyTime": "4.61",
        "gpa": 3.9,
        "rating": 88,
        "stars": 4,
        "jersey": "#86",
        "archetype": "Flex Mismatch",
        "summary": "Long, fluid pass catcher who threatens seams, flex alignments, and third-down mismatch packages.",
        "explanation": "Ideal for a coordinator who wants a detached tight end to stress linebackers without sacrificing red-zone size.",
        "notes": "Route pacing is ahead of schedule. Blocking profile is developmental but usable in motion-heavy looks.",
        "schemeFit": 90,
        "comparisonScore": 88,
        "confidenceScore": 85,
        "breakdown": {"physical": 88, "athletic": 86, "production": 80, "context": 82},
        "stats": {"receptions": 49, "receivingYards": 811, "touchdowns": 11, "yardsAfterCatch": 241},
        "topComparables": [2, 4, 1],
    },
    {
        "id": 7,
        "name": "Miles Turner",
        "school": "St. Frances Academy",
        "state": "MD",
        "city": "Baltimore",
        "classYear": 2026,
        "position": "EDGE",
        "projectedPosition": "Stand-up Edge",
        "type": "High School",
        "height": "6'4\"",
        "weight": 241,
        "fortyTime": "4.66",
        "gpa": 3.2,
        "rating": 86,
        "stars": 3,
        "jersey": "#9",
        "archetype": "Pressure Specialist",
        "summary": "Long outside rusher with real first-step speed and enough bend to threaten the corner.",
        "explanation": "High-variance edge prospect who fits best in an aggressive front that creates wide rush tracks and games.",
        "notes": "Pass-rush flashes are premium. Needs more snap-to-snap consistency against the run.",
        "schemeFit": 84,
        "comparisonScore": 85,
        "confidenceScore": 79,
        "breakdown": {"physical": 83, "athletic": 88, "production": 77, "context": 80},
        "stats": {"sacks": 11, "pressures": 36, "tacklesForLoss": 15, "qbHits": 19},
        "topComparables": [3, 5, 2],
    },
]

EXAMPLE_SHORTLISTS = [
    {
        "id": "priority-board",
        "name": "Priority Board",
        "color": "#ffb75e",
        "slots": [
            {"position": "QB", "playerId": 1},
            {"position": "WR", "playerId": 2},
            {"position": "CB", "playerId": 5},
        ],
    },
    {
        "id": "midwest-targets",
        "name": "Midwest Targets",
        "color": "#79c8ff",
        "slots": [
            {"position": "QB", "playerId": 1},
            {"position": "LB", "playerId": 3},
            {"position": "CB", "playerId": 5},
        ],
    },
    {
        "id": "late-cycle",
        "name": "Late Cycle Values",
        "color": "#8dd8a7",
        "slots": [
            {"position": "QB", "playerId": 4},
            {"position": "EDGE", "playerId": 7},
        ],
    },
]

EXAMPLE_ARCHETYPES = [
    {
        "id": "archetype-running-qb",
        "name": "Running QB",
        "position": "QB",
        "notes": "Dual-threat quarterback profile for zone-read and designed movement packages.",
        "minimums": [
            {"statKey": "rushYards", "minValue": 350},
            {"statKey": "passingYards", "minValue": 2200},
        ],
    },
    {
        "id": "archetype-boundary-x",
        "name": "Boundary X",
        "position": "WR",
        "notes": "Outside receiver profile for vertical shots and red-zone isolation.",
        "minimums": [
            {"statKey": "receivingYards", "minValue": 900},
            {"statKey": "touchdowns", "minValue": 10},
        ],
    },
]

EXAMPLE_ACTIVITY_FEED = [
    {
        "id": "act-1",
        "label": "Comparison run completed",
        "detail": "Evan Brooks vs Tyler Morris updated with a new production edge.",
        "time": "12 min ago",
    },
    {
        "id": "act-2",
        "label": "Shortlist updated",
        "detail": "Malik Dorsey moved into Priority Board after spring eval.",
        "time": "35 min ago",
    },
    {
        "id": "act-3",
        "label": "Coach note added",
        "detail": "Isaiah Ford tagged as a fit for pressure-heavy packages.",
        "time": "1 hr ago",
    },
    {
        "id": "act-4",
        "label": "Visit scheduled",
        "detail": "Caden Price set for an on-campus June visit.",
        "time": "Today",
    },
]

EXAMPLE_HISTORICAL_MATCHES = {
    1: [
        {"historicalId": "qb-hist-1", "name": "Jordan Reeves", "position": "QB", "school": "Oklahoma State", "conference": "Big 12", "lastSeason": 2023, "comparisonScores": {"physical": 90, "production": 93, "context": 84}},
        {"historicalId": "qb-hist-2", "name": "Malik James", "position": "QB", "school": "Appalachian State", "conference": "Sun Belt", "lastSeason": 2023, "comparisonScores": {"physical": 87, "production": 85, "context": 80}},
        {"historicalId": "qb-hist-3", "name": "Connor Hale", "position": "QB", "school": "Kansas State", "conference": "Big 12", "lastSeason": 2021, "comparisonScores": {"physical": 82, "production": 88, "context": 79}},
    ],
    2: [
        {"historicalId": "wr-hist-1", "name": "Marcus Hill", "position": "WR", "school": "Georgia", "conference": "SEC", "lastSeason": 2023, "comparisonScores": {"physical": 89, "production": 92, "context": 88}},
        {"historicalId": "wr-hist-2", "name": "Tyler Owens", "position": "WR", "school": "Michigan State", "conference": "Big Ten", "lastSeason": 2018, "comparisonScores": {"physical": 86, "production": 89, "context": 83}},
        {"historicalId": "wr-hist-3", "name": "DeShawn Brooks", "position": "WR", "school": "Toledo", "conference": "MAC", "lastSeason": 2023, "comparisonScores": {"physical": 82, "production": 84, "context": 78}},
    ],
    3: [
        {"historicalId": "lb-hist-1", "name": "Andre Wallace", "position": "LB", "school": "Wisconsin", "conference": "Big Ten", "lastSeason": 2022, "comparisonScores": {"physical": 84, "production": 90, "context": 87}},
        {"historicalId": "lb-hist-2", "name": "Micah Benton", "position": "LB", "school": "Kentucky", "conference": "SEC", "lastSeason": 2023, "comparisonScores": {"physical": 82, "production": 88, "context": 85}},
        {"historicalId": "lb-hist-3", "name": "Cole Mercer", "position": "LB", "school": "Iowa", "conference": "Big Ten", "lastSeason": 2021, "comparisonScores": {"physical": 79, "production": 85, "context": 84}},
    ],
    4: [
        {"historicalId": "qb-hist-4", "name": "Ethan Wade", "position": "QB", "school": "Wake Forest", "conference": "ACC", "lastSeason": 2022, "comparisonScores": {"physical": 88, "production": 84, "context": 86}},
        {"historicalId": "qb-hist-5", "name": "Jordan Reeves", "position": "QB", "school": "Oklahoma State", "conference": "Big 12", "lastSeason": 2023, "comparisonScores": {"physical": 86, "production": 82, "context": 88}},
        {"historicalId": "qb-hist-6", "name": "Parker Sloan", "position": "QB", "school": "BYU", "conference": "Big 12", "lastSeason": 2020, "comparisonScores": {"physical": 83, "production": 80, "context": 84}},
    ],
    5: [
        {"historicalId": "cb-hist-1", "name": "Kris Vaughn", "position": "CB", "school": "LSU", "conference": "SEC", "lastSeason": 2023, "comparisonScores": {"physical": 85, "production": 88, "context": 84}},
        {"historicalId": "cb-hist-2", "name": "Darius Cole", "position": "CB", "school": "Michigan", "conference": "Big Ten", "lastSeason": 2022, "comparisonScores": {"physical": 83, "production": 86, "context": 82}},
        {"historicalId": "cb-hist-3", "name": "Tre Holloway", "position": "CB", "school": "Louisville", "conference": "ACC", "lastSeason": 2021, "comparisonScores": {"physical": 80, "production": 84, "context": 81}},
    ],
    6: [
        {"historicalId": "te-hist-1", "name": "Logan Cross", "position": "TE", "school": "Utah", "conference": "Pac-12", "lastSeason": 2023, "comparisonScores": {"physical": 91, "production": 83, "context": 82}},
        {"historicalId": "te-hist-2", "name": "Brady Shelton", "position": "TE", "school": "Notre Dame", "conference": "Independent", "lastSeason": 2022, "comparisonScores": {"physical": 88, "production": 80, "context": 79}},
        {"historicalId": "te-hist-3", "name": "Mason Pike", "position": "TE", "school": "Kansas State", "conference": "Big 12", "lastSeason": 2021, "comparisonScores": {"physical": 84, "production": 78, "context": 77}},
    ],
    7: [
        {"historicalId": "edge-hist-1", "name": "Jermaine Pratt", "position": "EDGE", "school": "Penn State", "conference": "Big Ten", "lastSeason": 2023, "comparisonScores": {"physical": 86, "production": 82, "context": 80}},
        {"historicalId": "edge-hist-2", "name": "Quincy Reed", "position": "EDGE", "school": "Ole Miss", "conference": "SEC", "lastSeason": 2022, "comparisonScores": {"physical": 84, "production": 79, "context": 83}},
        {"historicalId": "edge-hist-3", "name": "Damon Graves", "position": "EDGE", "school": "NC State", "conference": "ACC", "lastSeason": 2021, "comparisonScores": {"physical": 82, "production": 77, "context": 78}},
    ],
}


def _average_score(scores):
    if hasattr(scores, "values"):
        iterable = scores.values()
    else:
        iterable = scores or []
    values = [value for value in iterable if isinstance(value, (int, float))]
    if not values:
        return 0
    return round(sum(values) / len(values))


def _normalize_example_player_id(player_id):
    if isinstance(player_id, int):
        return player_id
    if isinstance(player_id, str) and player_id.isdigit():
        return int(player_id)
    return player_id


def _build_historical_player(match):
    return {
        "id": match["historicalId"],
        "isHistorical": True,
        "name": match["name"],
        "school": match["school"],
        "state": match["conference"],
        "city": "",
        "classYear": match["lastSeason"],
        "position": match["position"],
        "projectedPosition": f"Historical {match['position']} Comparable",
        "type": "Historical",
        "height": "N/A",
        "weight": None,
        "fortyTime": "N/A",
        "gpa": None,
        "rating": _average_score(match.get("comparisonScores", {})),
        "stars": 0,
        "jersey": "HIST",
        "archetype": "Historical Match",
        "summary": f"Historical comparable from {match['school']} in the {match['conference']}.",
        "explanation": "This record captures how closely the historical player matches the selected recruit profile.",
        "notes": f"Most recent recorded season: {match['lastSeason']}. Historical player cards do not include related-athlete suggestions.",
        "schemeFit": _average_score(match.get("comparisonScores", {})),
        "comparisonScore": _average_score(match.get("comparisonScores", {})),
        "confidenceScore": _average_score(match.get("comparisonScores", {})),
        "breakdown": {
            "physical": match.get("comparisonScores", {}).get("physical"),
            "production": match.get("comparisonScores", {}).get("production"),
            "context": match.get("comparisonScores", {}).get("context"),
        },
        "stats": {
            "conference": match["conference"],
            "lastSeason": match["lastSeason"],
            "superScore": _average_score(match.get("comparisonScores", {})),
        },
        "topComparables": [],
    }


def _get_example_player(player_id):
    normalized_player_id = _coerce_int(player_id)
    record = _get_db_player(normalized_player_id)
    if not record or not record.get("is_recruit"):
        return None
    stats_map = _build_player_stats_map([normalized_player_id])
    metric_map = _build_player_metric_map([normalized_player_id])
    return _build_player_payload(record, stats_map=stats_map, metric_map=metric_map)


def _get_historical_player(player_id):
    normalized_player_id = _coerce_int(player_id)
    record = _get_db_player(normalized_player_id)
    if not record or record.get("is_recruit"):
        return None
    stats_map = _build_player_stats_map([normalized_player_id])
    metric_map = _build_player_metric_map([normalized_player_id])
    return _build_player_payload(record, stats_map=stats_map, metric_map=metric_map)


def _get_example_display_player(player_id):
    return _get_example_player(player_id) or _get_historical_player(player_id)


def _get_example_comparables(player):
    return []


def _get_example_historical_matches(player_id):
    normalized_player_id = _coerce_int(player_id)
    return _load_historical_matches(normalized_player_id)


def _filter_example_recruiting_players(args):
    limit = args.get("limit", type=int)
    players = _build_db_recruiting_players(args=args, order_by="p.name ASC", limit=limit)
    rating_floor = args.get("ratingFloor", type=float)
    if rating_floor is None:
        return players
    return [
        player for player in players
        if float(player.get("rating") or 0) >= rating_floor
    ]


def _build_example_recruiting_payload():
    players = _build_db_recruiting_players(order_by="p.id DESC")
    transfers = sum(1 for player in players if player.get("type") == "Transfer")
    ratings = [
        player.get("rating")
        for player in players
        if isinstance(player.get("rating"), (int, float))
    ]

    return {
        "dashboard": {
            "total_players": len(players),
            "transfers": transfers,
            "high_school": len(players) - transfers,
            "avg_rating": round(sum(ratings) / len(ratings)) if ratings else 0,
        },
        "players": players,
        "recentPlayers": players[:3],
        "lastTenRecruits": players[:10],
        "shortlists": _load_shortlists(limit=3),
        "activityFeed": [],
        "historicalMatches": {},
    }


_RECRUIT_TYPE_LABELS = {
    "high_school": "High School",
    "college": "College",
    "transfer": "Transfer",
}
_RECRUIT_TYPE_DB_VALUES = {
    "high school": "high_school",
    "high_school": "high_school",
    "college": "college",
    "transfer": "transfer",
}
_DEFAULT_SHORTLIST_COLOR = "#ffb75e"
_STATE_CODE_TO_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def _coerce_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _df_records(df):
    if df is None or df.empty:
        return []
    return df.where(df.notna(), None).to_dict(orient="records")


def _format_height(height_inches):
    if height_inches is None:
        return "N/A"
    try:
        total_inches = round(float(height_inches))
    except (TypeError, ValueError):
        return "N/A"
    feet = total_inches // 12
    inches = total_inches % 12
    return f"{feet}'{inches}\""


def _parse_height_inches(height_value):
    if height_value is None:
        return None
    if isinstance(height_value, (int, float)):
        return float(height_value)
    raw = str(height_value).strip()
    if not raw:
        return None
    if "'" in raw:
        feet_part, inches_part = raw.split("'", 1)
        inches_part = inches_part.replace('"', "").strip() or "0"
        try:
            return float(int(feet_part.strip()) * 12 + int(inches_part))
        except ValueError:
            return None
    try:
        return float(raw)
    except ValueError:
        return None


def _score_to_percent(value):
    if value is None:
        return 0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if numeric != numeric:
        return 0
    if numeric <= 1:
        numeric *= 100
    return round(numeric)


def _player_type_label(recruit_type, is_historical=False):
    if is_historical:
        return "Historical"
    return _RECRUIT_TYPE_LABELS.get((recruit_type or "").strip().lower(), "Recruit")


def _player_type_db_value(player_type):
    return _RECRUIT_TYPE_DB_VALUES.get((player_type or "").strip().lower())


def _state_name_from_code(state_code):
    if state_code is None:
        return None
    raw = str(state_code).strip()
    if not raw or raw.lower() == "nan":
        return None
    return _STATE_CODE_TO_NAME.get(raw.upper(), raw)


def _transfer_playing_time_key(frequency_player, conference):
    frequency = (frequency_player or "").strip().lower()
    conference_name = (conference or "").strip()
    power_conferences = {"SEC", "Big Ten", "Big 12", "ACC"}
    group_of_five = {"AAC", "Mountain West", "Sun Belt", "MAC", "CUSA"}

    if frequency == "starter":
        if conference_name in power_conferences:
            return "starter_p5"
        if conference_name in group_of_five:
            return "starter_g5"
        return "starter_fcs"
    if frequency == "backup":
        if conference_name in power_conferences:
            return "backup_p5"
        return "backup_g5"
    return "starter_d2"


def _query_players(is_recruit, args=None, order_by="p.name ASC", limit=None):
    args = args or {}
    query = (args.get("query") or args.get("q") or "").strip().lower()
    position = (args.get("position") or "All").strip()
    state = (args.get("state") or "All").strip()
    player_type = (args.get("type") or "All").strip()
    exclude_id = _coerce_int(args.get("excludeId"))

    sql = """
        SELECT
            p.id,
            p.name,
            p.team_name,
            p.is_recruit,
            pos.name AS position,
            p.height,
            p.weight,
            p.school_name,
            p.state_code,
            p.recruit_type,
            p.transfer_conference,
            p.play_year,
            p.notes
        FROM players p
        LEFT JOIN positions pos ON pos.id = p.position_id
        WHERE p.is_recruit = ?
    """
    params = [1 if is_recruit else 0]

    if exclude_id is not None:
        sql += " AND p.id <> ?"
        params.append(exclude_id)
    if query:
        sql += """
            AND LOWER(
                COALESCE(p.name, '') || ' ' ||
                COALESCE(pos.name, '') || ' ' ||
                COALESCE(p.school_name, '') || ' ' ||
                COALESCE(p.state_code, '')
            ) LIKE ?
        """
        params.append(f"%{query}%")
    if position != "All":
        sql += " AND pos.name = ?"
        params.append(position)
    if state != "All":
        sql += " AND p.state_code = ?"
        params.append(state)
    if player_type != "All":
        player_type_db = _player_type_db_value(player_type)
        if player_type_db:
            sql += " AND p.recruit_type = ?"
            params.append(player_type_db)

    sql += f" ORDER BY {order_by}"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    return _df_records(recruiting_db.custom_query_df(sql, tuple(params)))


def _build_player_stats_map(player_ids):
    valid_ids = [player_id for player_id in player_ids if player_id is not None]
    if not valid_ids:
        return {}

    placeholders = ",".join("?" for _ in valid_ids)
    df = recruiting_db.custom_query_df(
        f"""
        SELECT ps.player_id, s.name AS stat_name, ps.value
        FROM player_stats ps
        JOIN stats s ON s.id = ps.stat_id
        WHERE ps.player_id IN ({placeholders})
        ORDER BY ps.player_id, s.name
        """,
        tuple(valid_ids),
    )

    stats_map = {}
    for record in _df_records(df):
        stats_map.setdefault(record["player_id"], {})[record["stat_name"]] = record["value"]
    return stats_map


def _build_player_metric_map(player_ids):
    valid_ids = [player_id for player_id in player_ids if player_id is not None]
    if not valid_ids:
        return {}

    placeholders = ",".join("?" for _ in valid_ids)
    df = recruiting_db.custom_query_df(
        f"""
        SELECT
            p.id AS player_id,
            pe.confidence,
            pe.physical_score AS eval_physical_score,
            pe.production_score AS eval_production_score,
            pe.context_score AS eval_context_score,
            pc.final_score,
            pc.physical_score AS comp_physical_score,
            pc.production_score AS comp_production_score,
            pc.context_score AS comp_context_score
        FROM players p
        LEFT JOIN player_evaluations pe ON pe.id = p.evaluation_id
        LEFT JOIN player_comparisons pc ON pc.evaluation_id = p.evaluation_id
        WHERE p.id IN ({placeholders})
        """,
        tuple(valid_ids),
    )

    metric_map = {}
    for record in _df_records(df):
        metric_map[record["player_id"]] = record
    return metric_map


def _build_player_payload(record, stats_map=None, metric_map=None):
    stats_map = stats_map or {}
    metric_map = metric_map or {}
    player_id = record["id"]
    metrics = metric_map.get(player_id, {})
    is_historical = not bool(record.get("is_recruit", 1))

    physical = _score_to_percent(
        metrics.get("comp_physical_score") or metrics.get("eval_physical_score")
    )
    production = _score_to_percent(
        metrics.get("comp_production_score") or metrics.get("eval_production_score")
    )
    context = _score_to_percent(
        metrics.get("comp_context_score") or metrics.get("eval_context_score")
    )
    confidence = _score_to_percent(metrics.get("confidence"))
    rating = _score_to_percent(metrics.get("final_score"))
    if not rating:
        rating = _average_score([physical, production, context])

    position = record.get("position") or ""
    school_name = record.get("school_name") or record.get("team_name") or ""

    return {
        "id": player_id,
        "isHistorical": is_historical,
        "name": record.get("name") or "",
        "school": school_name,
        "state": record.get("state_code") or "",
        "city": "",
        "classYear": record.get("play_year"),
        "position": position,
        "projectedPosition": position or "Prospect",
        "type": _player_type_label(record.get("recruit_type"), is_historical=is_historical),
        "height": _format_height(record.get("height")),
        "weight": record.get("weight"),
        "fortyTime": "N/A",
        "gpa": None,
        "rating": rating,
        "stars": 0,
        "jersey": "N/A",
        "archetype": "",
        "summary": record.get("notes") or f"{position or 'Player'} profile from the recruiting database.",
        "explanation": record.get("notes") or "Stored player record from the recruiting database.",
        "notes": record.get("notes") or "",
        "schemeFit": rating,
        "comparisonScore": rating,
        "confidenceScore": confidence or rating,
        "breakdown": {
            "physical": physical,
            "production": production,
            "context": context,
        },
        "stats": stats_map.get(player_id, {}),
        "topComparables": [],
    }


def _build_db_recruiting_players(args=None, order_by="p.name ASC", limit=None):
    records = _query_players(True, args=args, order_by=order_by, limit=limit)
    player_ids = [record["id"] for record in records]
    stats_map = _build_player_stats_map(player_ids)
    metric_map = _build_player_metric_map(player_ids)
    return [
        _build_player_payload(record, stats_map=stats_map, metric_map=metric_map)
        for record in records
    ]


def _get_db_player(player_id):
    if player_id is None:
        return None
    records = _query_players(True) + _query_players(False)
    for record in records:
        if record["id"] == player_id:
            return record
    return None


def _load_shortlists(limit=None):
    records = _df_records(
        recruiting_db.custom_query_df(
            """
            SELECT
                s.id AS shortlist_id,
                s.name,
                s.color,
                sp.id AS slot_id,
                sp.slot_number,
                pos.name AS position,
                sa.player_id
            FROM schemes s
            LEFT JOIN scheme_positions sp ON sp.scheme_id = s.id
            LEFT JOIN positions pos ON pos.id = sp.position_id
            LEFT JOIN scheme_assignments sa ON sa.scheme_position_id = sp.id
            ORDER BY s.id DESC, sp.slot_number ASC
            """
        )
    )

    shortlists = []
    index = {}
    for record in records:
        shortlist_id = record["shortlist_id"]
        if shortlist_id not in index:
            payload = {
                "id": shortlist_id,
                "name": record.get("name") or "Untitled Group",
                "color": record.get("color") or _DEFAULT_SHORTLIST_COLOR,
                "slots": [],
            }
            index[shortlist_id] = payload
            shortlists.append(payload)

        if record.get("slot_id") is not None:
            index[shortlist_id]["slots"].append(
                {
                    "id": record["slot_id"],
                    "position": record.get("position"),
                    "playerId": record.get("player_id"),
                }
            )

    if limit is not None:
        shortlists = shortlists[:limit]
    return shortlists


def _load_archetypes():
    archetypes = []
    for record in _df_records(recruiting_db.get_archetypes_df()):
        minimums = []
        if record.get("stat_rule_stat") and record.get("stat_rule_min") is not None:
            minimums.append(
                {
                    "statKey": record["stat_rule_stat"],
                    "minValue": record["stat_rule_min"],
                }
            )
        archetypes.append(
            {
                "id": record["id"],
                "name": record["title"],
                "position": record.get("position"),
                "notes": record.get("notes") or "",
                "minimums": minimums,
            }
        )
    return archetypes


def _get_player_row(player_id):
    records = _df_records(
        recruiting_db.custom_query_df(
            """
            SELECT
                p.id,
                p.name,
                p.team_name,
                p.is_recruit,
                p.evaluation_id,
                pos.name AS position,
                p.height,
                p.weight,
                p.school_name,
                p.state_code,
                p.recruit_type,
                p.school_strength,
                p.transfer_conference,
                p.play_year,
                p.frequency_player,
                p.notes
            FROM players p
            LEFT JOIN positions pos ON pos.id = p.position_id
            WHERE p.id = ?
            LIMIT 1
            """,
            (player_id,),
        )
    )
    return records[0] if records else None


def _get_player_stats(player_id):
    return _build_player_stats_map([player_id]).get(player_id, {})


def _build_eval_recruit_dict(player_record, stats_map):
    recruit_type = "transfer" if player_record.get("recruit_type") == "transfer" else "highschool"
    return {
        "name": player_record.get("name") or "",
        "position": player_record.get("position") or "",
        "season": player_record.get("play_year") or 2024,
        "recruit_type": recruit_type,
        "home_state": _state_name_from_code(player_record.get("state_code")),
        "hs_school_strength": player_record.get("school_strength") or "average",
        "transfer_conference": player_record.get("transfer_conference"),
        "transfer_playing_time": _transfer_playing_time_key(
            player_record.get("frequency_player"),
            player_record.get("transfer_conference"),
        ),
        "height": player_record.get("height"),
        "weight": player_record.get("weight"),
        "stats": stats_map,
    }


def _build_historical_career_profiles():
    rows = _df_records(
        recruiting_db.custom_query_df(
            """
            SELECT
                p.id AS player_id,
                p.name AS player,
                pos.name AS position,
                COALESCE(p.play_year, 2024) AS season,
                p.height AS bio_height,
                p.weight AS bio_weight,
                p.transfer_conference AS conference,
                p.state_code AS bio_homeState,
                s.name AS stat_name,
                ps.value AS stat_value
            FROM players p
            LEFT JOIN positions pos ON pos.id = p.position_id
            LEFT JOIN player_stats ps ON ps.player_id = p.id
            LEFT JOIN stats s ON s.id = ps.stat_id
            WHERE p.is_recruit = 0
            ORDER BY p.id
            """
        )
    )

    merged_rows = {}
    for row in rows:
        player_id = str(row["player_id"])
        if player_id not in merged_rows:
            merged_rows[player_id] = {
                "player_id": player_id,
                "player": row.get("player"),
                "position": row.get("position"),
                "season": row.get("season"),
                "bio_height": row.get("bio_height"),
                "bio_weight": row.get("bio_weight"),
                "conference": row.get("conference"),
                "bio_homeState": _state_name_from_code(row.get("bio_homeState")),
            }
        stat_name = row.get("stat_name")
        if isinstance(stat_name, str) and stat_name.startswith("stat_"):
            merged_rows[player_id][stat_name] = row.get("stat_value")

    return pe.build_career_profiles(list(merged_rows.values()))


def _store_player_evaluation(player_id):
    player_record = _get_player_row(player_id)
    if not player_record or not player_record.get("is_recruit"):
        return None

    stats_map = _get_player_stats(player_id)
    recruit_dict = _build_eval_recruit_dict(player_record, stats_map)
    recruit_scores = player_metrics.player_score(
        position=recruit_dict["position"],
        recruit_type=recruit_dict["recruit_type"],
        height=recruit_dict["height"],
        weight=recruit_dict["weight"],
        stats=recruit_dict["stats"],
        home_state=recruit_dict["home_state"],
        hs_school_strength=recruit_dict["hs_school_strength"],
        transfer_conference=recruit_dict["transfer_conference"],
        transfer_playing_time=recruit_dict["transfer_playing_time"],
    )

    evaluation_id = player_record.get("evaluation_id")
    eval_kwargs = {
        "height": recruit_dict["height"],
        "weight": recruit_dict["weight"],
        "context_multiplier": recruit_scores["context"]["multiplier"],
        "confidence": 0,
        "physical_score": recruit_scores["physical"]["score"],
        "production_score": recruit_scores["production"]["score"],
        "context_score": recruit_scores["context"]["score"],
    }
    if evaluation_id:
        recruiting_db.update_player_evaluation(evaluation_id, **eval_kwargs)
    else:
        evaluation_id = recruiting_db.insert_player_evaluation(player_id, **eval_kwargs)

    return {
        "evaluation_id": evaluation_id,
        "recruit_dict": recruit_dict,
        "recruit_scores": recruit_scores,
    }


def _run_player_comparison(player_id):
    player_record = _get_player_row(player_id)
    if not player_record or not player_record.get("is_recruit"):
        return None

    evaluation_info = _store_player_evaluation(player_id)
    if not evaluation_info:
        return None

    evaluation_result = pe.evaluate(
        pe.Recruit(**evaluation_info["recruit_dict"]),
        _build_historical_career_profiles(),
        top_n=3,
    )
    recruit_confidence = evaluation_result.recruit_profile.confidence * 100
    recruiting_db.update_player_evaluation(
        evaluation_info["evaluation_id"],
        confidence=recruit_confidence,
        context_multiplier=evaluation_result.recruit_profile.context_multiplier,
    )

    top_match = evaluation_result.top_matches[0] if evaluation_result.top_matches else None
    if top_match:
        recruiting_db.insert_player_comparison(
            evaluation_id=evaluation_info["evaluation_id"],
            final_score=top_match.final_score,
            confidence=top_match.confidence * 100,
            recency_weight=top_match.recency_weight,
            physical_score=top_match.physical.score,
            physical_height=top_match.physical.height_sim,
            physical_weight=top_match.physical.weight_sim,
            production_score=top_match.production.score,
            production_stats_used=top_match.production.fields_used,
            production_stats_missing=top_match.production.fields_missing,
            context_score=top_match.context.score,
            context_recruit=top_match.context.recruit_multiplier,
            context_comp=top_match.context.comparable_multiplier,
        )

    return evaluation_result


def _evaluation_matches_to_payload(evaluation_result):
    payload = []
    for match in evaluation_result.top_matches:
        comparison_scores = {
            "physical": _score_to_percent(match.physical.score),
            "production": _score_to_percent(match.production.score),
            "context": _score_to_percent(match.context.score),
        }
        payload.append(
            {
                "historicalId": _coerce_int(match.player_id) or match.player_id,
                "name": match.name,
                "position": evaluation_result.position,
                "school": "",
                "conference": "",
                "lastSeason": None,
                "comparisonScores": comparison_scores,
                "superScore": _average_score(comparison_scores.values()),
            }
        )

    if not payload:
        return payload

    historical_rows = {
        str(row["id"]): row
        for row in _query_players(False, args={"position": evaluation_result.position}, order_by="p.play_year DESC, p.name ASC")
    }
    for item in payload:
        row = historical_rows.get(str(item["historicalId"]))
        if row:
            item["school"] = row.get("school_name") or row.get("team_name") or ""
            item["conference"] = row.get("transfer_conference") or row.get("team_name") or ""
            item["lastSeason"] = row.get("play_year")
    return payload


def _load_historical_matches(player_id):
    recruit = _get_player_row(player_id)
    if not recruit or not recruit.get("is_recruit"):
        return []
    evaluation_result = _run_player_comparison(player_id)
    if not evaluation_result:
        return []
    return _evaluation_matches_to_payload(evaluation_result)


@app.route("/api/example_recruiting_data")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_example_recruiting_data():
    return jsonify(_build_example_recruiting_payload())


@app.route("/api/recruits")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_recruits():
    players = _filter_example_recruiting_players(request.args)
    all_players = _build_db_recruiting_players(order_by="p.name ASC")
    return jsonify(
        {
            "players": players,
            "positions": sorted({player.get("position") for player in all_players if player.get("position")}),
            "states": sorted({player.get("state") for player in all_players if player.get("state")}),
            "types": sorted({player.get("type") for player in all_players if player.get("type")}),
            "total": len(players),
        }
    )


@app.route("/api/recruits/<player_id>")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_recruit(player_id):
    normalized_player_id = _coerce_int(player_id)
    player = _get_example_display_player(normalized_player_id)
    if not player:
        return jsonify({"error": "player_not_found"}), 404

    previous_player_id = None
    next_player_id = None
    if not player.get("isHistorical"):
        recruits = _build_db_recruiting_players(order_by="p.name ASC")
        for index, recruit in enumerate(recruits):
            if recruit.get("id") == player.get("id"):
                previous_player_id = recruits[index - 1]["id"] if index > 0 else None
                next_player_id = (
                    recruits[index + 1]["id"]
                    if index < len(recruits) - 1
                    else None
                )
                break

    return jsonify(
        {
            "player": player,
            "comparables": [] if player.get("isHistorical") else _get_example_comparables(player),
            "previousPlayerId": previous_player_id,
            "nextPlayerId": next_player_id,
        }
    )


@app.route("/api/recruits/<player_id>", methods=["DELETE"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def delete_recruit(player_id):
    normalized_player_id = _coerce_int(player_id)
    player = _get_db_player(normalized_player_id)
    if not player:
        return jsonify({"error": "player_not_found"}), 404

    recruiting_db.delete_player(normalized_player_id)
    return jsonify({"ok": True, "playerId": normalized_player_id})


@app.route("/api/recruits/<player_id>/historical_matches")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_recruit_historical_matches(player_id):
    return jsonify(_get_example_historical_matches(player_id))


@app.route("/api/recruits/evaluate_all", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def evaluate_all_recruits():
    recruit_rows = _query_players(True, order_by="p.id ASC")
    recruit_ids = [row["id"] for row in recruit_rows if row.get("id") is not None]

    evaluated = 0
    failed = 0
    failures = []

    for recruit_id in recruit_ids:
        try:
            result = _run_player_comparison(recruit_id)
            if result is None:
                failed += 1
                failures.append({"playerId": recruit_id, "error": "evaluation_not_available"})
            else:
                evaluated += 1
        except Exception as exc:
            failed += 1
            failures.append({"playerId": recruit_id, "error": str(exc)})

    return jsonify(
        {
            "status": "ok",
            "total": len(recruit_ids),
            "evaluated": evaluated,
            "failed": failed,
            "failures": failures[:25],
        }
    )

@app.route("/api/dashboard_info")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_dashboard_info():
    return jsonify(_build_example_recruiting_payload()["dashboard"])

@app.route("/api/top_3_most_recent_recruits")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_top_3_most_recent_recruits():
    return jsonify(_build_example_recruiting_payload()["recentPlayers"])

@app.route("/api/recent_shortlists")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_recent_shortlists():
    return jsonify(_load_shortlists(limit=3))

@app.route("/api/shortlists")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_shortlists():
    return jsonify(_load_shortlists())

@app.route("/api/shortlists", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def create_shortlist():
    data = request.get_json() or {}
    name = (data.get("name") or "Untitled Group").strip() or "Untitled Group"
    color = (data.get("color") or _DEFAULT_SHORTLIST_COLOR).strip() or _DEFAULT_SHORTLIST_COLOR
    shortlist_id = recruiting_db.insert_scheme(user_id=None, name=name, color=color)

    for index, slot in enumerate(data.get("slots") or [], start=1):
        position = (slot.get("position") or "").strip()
        if not position:
            continue
        position_id = recruiting_db.get_or_create_position(position)
        recruiting_db.insert_scheme_position(shortlist_id, index, position_id=position_id)

    shortlist = next(
        (item for item in _load_shortlists() if item["id"] == shortlist_id),
        {"id": shortlist_id, "name": name, "color": color, "slots": []},
    )
    return jsonify({"status": "ok", "shortlist": shortlist})

@app.route("/api/shortlists/<shortlist_id>", methods=["DELETE"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def delete_shortlist(shortlist_id):
    normalized_shortlist_id = _coerce_int(shortlist_id)
    if normalized_shortlist_id is None:
        return jsonify({"error": "shortlist_not_found"}), 404
    recruiting_db.delete_scheme(normalized_shortlist_id)
    return jsonify({"status": "ok", "shortlistId": normalized_shortlist_id})

@app.route("/api/shortlists/<shortlist_id>/assign_player", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def assign_shortlist_player(shortlist_id):
    data = request.get_json() or {}
    normalized_shortlist_id = _coerce_int(shortlist_id)
    player_id = _coerce_int(data.get("playerId"))
    position = (data.get("position") or "").strip()
    if normalized_shortlist_id is None:
        return jsonify({"error": "shortlist_not_found"}), 404
    if player_id is None or not position:
        return jsonify({"error": "invalid_assignment"}), 400

    slot_df = recruiting_db.custom_query_df(
        """
        SELECT sp.id
        FROM scheme_positions sp
        JOIN positions pos ON pos.id = sp.position_id
        WHERE sp.scheme_id = ? AND pos.name = ?
        ORDER BY sp.slot_number ASC
        LIMIT 1
        """,
        (normalized_shortlist_id, position),
    )
    slot_records = _df_records(slot_df)
    if not slot_records:
        return jsonify({"error": "slot_not_found"}), 404

    recruiting_db.assign_recruit_to_scheme_position(slot_records[0]["id"], player_id)
    return jsonify({"status": "ok", "shortlistId": normalized_shortlist_id, "assignment": data})

@app.route("/api/shortlists/<shortlist_id>/clear_player", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def clear_shortlist_player(shortlist_id):
    data = request.get_json() or {}
    normalized_shortlist_id = _coerce_int(shortlist_id)
    slot_id = _coerce_int(data.get("slotId"))
    if normalized_shortlist_id is None:
        return jsonify({"error": "shortlist_not_found"}), 404
    if slot_id is None:
        return jsonify({"error": "slot_not_found"}), 400

    recruiting_db.remove_recruit_from_scheme_position(slot_id)
    return jsonify({"status": "ok", "shortlistId": normalized_shortlist_id, "cleared": {"slotId": slot_id}})

@app.route("/api/shortlists/<shortlist_id>/slots", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def add_shortlist_slot(shortlist_id):
    data = request.get_json() or {}
    normalized_shortlist_id = _coerce_int(shortlist_id)
    position = (data.get("position") or "").strip()
    if normalized_shortlist_id is None:
        return jsonify({"error": "shortlist_not_found"}), 404
    if not position:
        return jsonify({"error": "position_required"}), 400

    max_slot_df = recruiting_db.custom_query_df(
        "SELECT COALESCE(MAX(slot_number), 0) AS max_slot FROM scheme_positions WHERE scheme_id = ?",
        (normalized_shortlist_id,),
    )
    next_slot_number = (_df_records(max_slot_df)[0]["max_slot"] or 0) + 1
    position_id = recruiting_db.get_or_create_position(position)
    slot_id = recruiting_db.insert_scheme_position(
        normalized_shortlist_id,
        next_slot_number,
        position_id=position_id,
    )

    return jsonify(
        {
            "status": "ok",
            "shortlistId": normalized_shortlist_id,
            "slot": {"id": slot_id, "position": position, "playerId": None},
        }
    )

@app.route("/api/shortlists/<shortlist_id>/slots/<slot_id>", methods=["DELETE"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def remove_shortlist_slot(shortlist_id, slot_id):
    normalized_shortlist_id = _coerce_int(shortlist_id)
    normalized_slot_id = _coerce_int(slot_id)
    if normalized_shortlist_id is None or normalized_slot_id is None:
        return jsonify({"error": "slot_not_found"}), 404

    with recruiting_db.get_conn() as conn:
        conn.execute(
            "DELETE FROM scheme_assignments WHERE scheme_position_id = ?",
            (normalized_slot_id,),
        )
        conn.execute(
            "DELETE FROM scheme_positions WHERE id = ? AND scheme_id = ?",
            (normalized_slot_id, normalized_shortlist_id),
        )

    return jsonify({"status": "ok", "shortlistId": normalized_shortlist_id, "slotId": normalized_slot_id})

@app.route("/api/archetypes")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_archetypes():
    return jsonify(_load_archetypes())

@app.route("/api/archetypes", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def create_archetype():
    data = request.get_json() or {}
    name = (data.get("name") or "Untitled Archetype").strip() or "Untitled Archetype"
    position_name = (data.get("position") or "").strip()
    notes = (data.get("notes") or "").strip()
    minimums = data.get("minimums") or []

    position_id = recruiting_db.get_or_create_position(position_name) if position_name else None
    stat_rule_id = None
    if minimums:
        first_rule = minimums[0]
        stat_key = (first_rule.get("statKey") or "").strip()
        min_value = first_rule.get("minValue")
        if stat_key and min_value is not None:
            stat_id = recruiting_db.get_stat_id(stat_key, position_id)
            if stat_id is None:
                stat_id = recruiting_db.insert_stat(stat_key, position_id)
            stat_rule_id = recruiting_db.insert_stat_rule(stat_id, float(min_value))

    archetype_id = recruiting_db.insert_archetype(
        title=name,
        position_id=position_id,
        notes=notes or None,
        stat_rule_id=stat_rule_id,
    )
    archetype = next(
        (item for item in _load_archetypes() if item["id"] == archetype_id),
        {"id": archetype_id, "name": name, "position": position_name, "notes": notes, "minimums": minimums[:1]},
    )
    return jsonify({"status": "ok", "archetype": archetype})

@app.route("/api/archetypes/<archetype_id>", methods=["DELETE"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def delete_archetype(archetype_id):
    normalized_archetype_id = _coerce_int(archetype_id)
    if normalized_archetype_id is None:
        return jsonify({"error": "archetype_not_found"}), 404
    recruiting_db.delete_archetype(normalized_archetype_id)
    return jsonify({"status": "ok", "archetypeId": normalized_archetype_id})

@app.route("/api/create_player", methods=["POST"])
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def create_player():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    position_name = (data.get("position") or "").strip()
    if not name or not position_name:
        return jsonify({"error": "missing_required_fields"}), 400

    position_id = recruiting_db.get_or_create_position(position_name)
    recruit_type = _player_type_db_value(data.get("type")) or "high_school"
    player_id = recruiting_db.insert_player(
        name=name,
        position_id=position_id,
        is_recruit=True,
        notes=(data.get("summary") or "").strip() or None,
        height=_parse_height_inches(data.get("height")),
        weight=data.get("weight"),
        school_name=(data.get("school") or "").strip() or None,
        state_code=(data.get("state") or "").strip() or None,
        recruit_type=recruit_type,
        play_year=_coerce_int(data.get("classYear")),
    )

    for stat_name, stat_value in (data.get("stats") or {}).items():
        if stat_value in ("", None):
            continue
        stat_id = recruiting_db.get_stat_id(stat_name, position_id)
        if stat_id is None:
            stat_id = recruiting_db.insert_stat(stat_name, position_id)
        recruiting_db.insert_player_stat(player_id, stat_id, float(stat_value))

    _store_player_evaluation(player_id)
    created_player = _get_example_player(player_id)
    return jsonify({"status": "ok", "player": created_player or {"id": player_id}})

@app.route("/api/get_last_10_recruits")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_last_10_recruits():
    return jsonify(_build_example_recruiting_payload()["lastTenRecruits"])

# =========================================================
# Local Dev Entrypoint
# =========================================================

if __name__ == "__main__":
    # For local development only.
    # In production this would normally be run by Gunicorn/uWSGI/etc.
    debug = _env_bool("FLASK_DEBUG", default=False)
    app.run(port=5000, debug=debug)
