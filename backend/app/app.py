import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler
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

from db import (
    attach_subject_to_user,
    delete_user,
    get_user_by_email,
    get_user_by_subject,
    get_user_list,
    init_db,
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

init_db()  # Create tables if needed.

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

@app.route("/api/dashboard_info")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_dashboard_info():

    data = {
        "total_players": 7,
        "transfers": 2,
        "high_school": 5,
        "avg_rating": 89
    }

    return jsonify(data)

@app.route("/api/top_3_most_recent_recruits")
@require_role("SUPER_ADMIN", "ADMIN", "COACH")
def get_top_3_most_recent_recruits():

    players = [
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
        "breakdown": {
        "physical": 82,
        "athletic": 79,
        "production": 94,
        "context": 87
        },
        "stats": {
        "passingYards": 3248,
        "touchdowns": 34,
        "interceptions": 6,
        "rushYards": 512
        },
        "topComparables": [4, 6, 7]
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
        "breakdown": {
        "physical": 86,
        "athletic": 94,
        "production": 89,
        "context": 85
        },
        "stats": {
        "receptions": 71,
        "receivingYards": 1284,
        "touchdowns": 16,
        "contestedCatchRate": "68%"
        },
        "topComparables": [5, 6, 4]
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
        "breakdown": {
        "physical": 81,
        "athletic": 90,
        "production": 88,
        "context": 89
        }
    }
    ]

    return jsonify(players)

# =========================================================
# Local Dev Entrypoint
# =========================================================

if __name__ == "__main__":
    # For local development only.
    # In production this would normally be run by Gunicorn/uWSGI/etc.
    debug = _env_bool("FLASK_DEBUG", default=False)
    app.run(port=5000, debug=debug)
