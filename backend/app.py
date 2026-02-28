import os
import uuid
import secrets
from datetime import timedelta
from functools import wraps

import msal
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

from db import (
    init_db,
    get_user_by_email,
    get_user_by_subject,
    attach_subject_to_user,
    accept_invite,
    create_invite,
    list_users,
)

load_dotenv()

# ----------------------------
# App setup
# ----------------------------
app = Flask(__name__)

secret = os.getenv("FLASK_SECRET_KEY")
if not secret:
    raise RuntimeError("FLASK_SECRET_KEY must be set")
app.secret_key = secret

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
API_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",") if o.strip()]

# Cookie / session hardening (safe locally)
cookie_secure = os.getenv("COOKIE_SECURE", "0").strip() == "1"  # set to 1 behind https
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=cookie_secure,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.getenv("SESSION_HOURS", "8"))),
)

# CORS (cookies enabled)
CORS(app, supports_credentials=True, origins=API_ORIGINS)

# Security headers (configured so it won’t break local dev)
# If you embed external scripts/styles later, you’ll tighten CSP then.
talisman_csp = {
    "default-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],  # allow Vite dev
    "connect-src": ["'self'"] + API_ORIGINS,
}
Talisman(
    app,
    content_security_policy=talisman_csp,
    force_https=False,  # local dev stays http
)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "300 per hour")],
)

# ----------------------------
# Microsoft OAuth config
# ----------------------------
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
TENANT = os.getenv("MICROSOFT_TENANT", "common")
REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:5000/auth/microsoft/callback")

ALLOWED_EMAIL_DOMAINS = [
    d.strip().lower()
    for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",")
    if d.strip()
]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"
SCOPES = ["User.Read"]

init_db(os.getenv("SEED_SUPER_ADMIN_EMAIL"))


def _build_msal_app():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("Missing MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET in .env")
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )


def _email_domain_allowed(email: str) -> bool:
    email = (email or "").lower()
    if "@" not in email:
        return False
    domain = email.split("@", 1)[1]
    return (not ALLOWED_EMAIL_DOMAINS) or (domain in ALLOWED_EMAIL_DOMAINS)


# ----------------------------
# CSRF (double-submit style)
# ----------------------------
def _ensure_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _require_csrf():
    # Only protect state-changing routes that use cookies
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        sent = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not expected or not sent or sent != expected:
            return jsonify({"error": "csrf_failed"}), 403
    return None


@app.before_request
def _csrf_guard():
    # Allow OAuth callback + health without CSRF
    if request.path.startswith("/auth/microsoft/callback") or request.path == "/health":
        return None
    # Allow login redirect endpoint without CSRF (it is GET)
    if request.path.startswith("/auth/microsoft/login"):
        return None
    return _require_csrf()


# ----------------------------
# AuthZ helper
# ----------------------------
def require_role(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                return jsonify({"error": "not_authenticated"}), 401
            if user.get("role") not in roles:
                return jsonify({"error": "forbidden", "required": roles}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/csrf")
def api_csrf():
    # frontend calls this once and stores token
    return jsonify({"csrfToken": _ensure_csrf_token()})


@app.get("/auth/microsoft/login")
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "30 per minute"))
def microsoft_login():
    state = str(uuid.uuid4())
    session["oauth_state"] = state
    session.permanent = True  # enable PERMANENT_SESSION_LIFETIME

    auth_url = _build_msal_app().get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state,
        prompt="select_account",
    )
    return redirect(auth_url)


@app.get("/auth/microsoft/callback")
@limiter.limit(os.getenv("RATE_LIMIT_CALLBACK", "60 per minute"))
def microsoft_callback():
    # One-time state check
    expected_state = session.pop("oauth_state", None)
    if request.args.get("state") != expected_state:
        return "Invalid state", 400

    code = request.args.get("code")
    if not code:
        # Don’t leak too much detail
        return "Missing authorization code.", 400

    token = _build_msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    if "access_token" not in token:
        # Avoid echoing full provider error to the browser
        return "Login failed while acquiring token.", 400

    access_token = token["access_token"]
    claims = token.get("id_token_claims") or {}
    tid = claims.get("tid") or "unknown"

    # Fetch user profile
    me = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if me.status_code != 200:
        return "Login failed while fetching profile.", 400

    profile = me.json()
    oid = profile.get("id")  # object id within tenant
    email = (profile.get("mail") or profile.get("userPrincipalName") or "").lower()
    name = profile.get("displayName") or ""

    if not _email_domain_allowed(email):
        return "Access not granted (domain not allowed).", 403

    subject = f"{tid}:{oid}" if tid and oid else None

    # Ensure CSRF token exists for this session now that user is logged in
    _ensure_csrf_token()

    # ---- Invite-only gate ----
    # 1) Match by subject
    if subject:
        u = get_user_by_subject(subject)
        if u and u["is_active"] == 1:
            session["user"] = {"email": u["email"], "role": u["role"], "name": name, "subject": subject}
            return redirect(FRONTEND_URL + "/")

    # 2) Match by email
    u = get_user_by_email(email)
    if u and u["is_active"] == 1:
        if subject and not u["provider_subject"]:
            attach_subject_to_user(email, subject)
        session["user"] = {"email": u["email"], "role": u["role"], "name": name, "subject": subject}
        return redirect(FRONTEND_URL + "/")

    # 3) Accept invite if exists
    accepted = accept_invite(email)
    if accepted == "accepted":
        u2 = get_user_by_email(email)
        if subject:
            attach_subject_to_user(email, subject)
        session["user"] = {"email": u2["email"], "role": u2["role"], "name": name, "subject": subject}
        return redirect(FRONTEND_URL + "/")

    return "Access not granted. Contact your administrator.", 403


@app.post("/auth/logout")
@limiter.limit(os.getenv("RATE_LIMIT_LOGOUT", "30 per minute"))
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    # Always make sure a CSRF token exists for clients that are logged in
    if session.get("user"):
        _ensure_csrf_token()
    return jsonify(session.get("user"))


@app.get("/api/users")
@require_role("SUPER_ADMIN", "ADMIN")
def api_users():
    return jsonify({"users": list_users()})


@app.post("/api/invite")
@require_role("SUPER_ADMIN")
@limiter.limit(os.getenv("RATE_LIMIT_INVITE", "20 per minute"))
def api_invite():
    if not request.is_json:
        return jsonify({"error": "expected_json"}), 400

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "").strip().upper()

    if not email or "@" not in email:
        return jsonify({"error": "invalid_email"}), 400
    if not _email_domain_allowed(email):
        return jsonify({"error": "email_domain_not_allowed"}), 400
    if role not in {"SUPER_ADMIN", "ADMIN", "COACH", "SCOUT"}:
        return jsonify({"error": "invalid_role"}), 400

    inviter = session["user"]["email"]
    result = create_invite(email=email, role=role, invited_by_email=inviter)
    return jsonify({"ok": True, "result": result})


if __name__ == "__main__":
    # Keep debug local-only. Use FLASK_DEBUG=1 when you need it.
    debug = os.getenv("FLASK_DEBUG", "0").strip() == "1"
    app.run(port=5000, debug=debug)