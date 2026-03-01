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
    # users
    get_user_by_email,
    get_user_by_subject,
    create_user_if_missing,
    attach_subject_to_user,
    # orgs / memberships
    create_org,
    get_org,
    list_orgs_for_user,
    get_membership,
    upsert_membership,
    count_active_members,
    list_members,
    deactivate_membership,
    delete_membership,
    # invites
    create_invite,
    accept_valid_invites_for_user,
    has_valid_invite,
    # system
    list_users_system,
    list_orgs_system,
    delete_org,
    set_team_admin,
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

cookie_secure = os.getenv("COOKIE_SECURE", "0").strip() == "1"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.getenv("SESSION_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=cookie_secure,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.getenv("SESSION_HOURS", "8"))),
)

CORS(app, supports_credentials=True, origins=API_ORIGINS)

talisman_csp = {
    "default-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
    "connect-src": ["'self'"] + API_ORIGINS,
}
Talisman(app, content_security_policy=talisman_csp, force_https=False)

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

ALLOWED_EMAIL_DOMAINS = [d.strip().lower() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",") if d.strip()]

AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"
SCOPES = ["User.Read"]

DEFAULT_ORG_SEAT_LIMIT = int(os.getenv("DEFAULT_ORG_SEAT_LIMIT", "25"))

init_db(os.getenv("SEED_SUPER_ADMIN_EMAIL"), default_org_seat_limit=DEFAULT_ORG_SEAT_LIMIT)


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
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        sent = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not expected or not sent or sent != expected:
            return jsonify({"error": "csrf_failed"}), 403
    return None


@app.before_request
def _csrf_guard():
    if request.path.startswith("/auth/microsoft/callback") or request.path == "/health":
        return None
    if request.path.startswith("/auth/microsoft/login"):
        return None
    return _require_csrf()


# ----------------------------
# Auth helpers
# ----------------------------
def _session_user():
    return session.get("user")


def _clear_active_org():
    if session.get("user"):
        session["user"]["orgId"] = None
        session["user"]["role"] = None

def _validate_active_org_membership() -> bool:
    """Ensure session.user.orgId/role points to a real active membership.
    If invalid (stale cookie after DB reset, deleted org, etc.), clears orgId/role.
    Returns True if valid, False otherwise.
    """
    u = session.get("user") or {}
    if not u.get("orgId") or not u.get("role") or not u.get("userId"):
        return False
    try:
        org_id = int(u.get("orgId"))
        user_id = int(u.get("userId"))
    except Exception:
        _clear_active_org()
        return False
    org = get_org(org_id)
    if not org:
        _clear_active_org()
        return False
    m = get_membership(user_id, org_id)
    if not m or m["is_active"] != 1:
        _clear_active_org()
        return False
    # keep role in sync with DB
    session["user"]["orgId"] = org_id
    session["user"]["role"] = m["role"]
    return True


def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = _session_user()
        if not u:
            return jsonify({"error": "not_authenticated"}), 401
        return fn(*args, **kwargs)
    return wrapper


def require_system_role(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = _session_user()
            if not u:
                return jsonify({"error": "not_authenticated"}), 401
            if (u.get("systemRole") or "") not in roles:
                return jsonify({"error": "forbidden", "required": roles}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco



def require_org_role(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = _session_user()
            if not u:
                return jsonify({"error": "not_authenticated"}), 401

            # Stale sessions happen if DB reset / org deleted. Validate and clear if needed.
            if not _validate_active_org_membership():
                return jsonify({"error": "no_active_org"}), 409

            if u.get("role") not in roles:
                return jsonify({"error": "forbidden", "required": roles}), 403

            return fn(*args, **kwargs)
        return wrapper
    return deco



def _set_active_org_for_user(user_id: int, org_id: int):
    m = get_membership(user_id=user_id, org_id=org_id)
    if not m or m["is_active"] != 1:
        return False
    session["user"]["orgId"] = int(org_id)
    session["user"]["role"] = m["role"]
    return True


# ----------------------------
# Routes
# ----------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/csrf")
def api_csrf():
    return jsonify({"csrfToken": _ensure_csrf_token()})


@app.get("/auth/microsoft/login")
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "30 per minute"))
def microsoft_login():
    state = str(uuid.uuid4())
    session["oauth_state"] = state
    session.permanent = True

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
    expected_state = session.pop("oauth_state", None)
    if request.args.get("state") != expected_state:
        return "Invalid state", 400

    code = request.args.get("code")
    if not code:
        return "Missing authorization code.", 400

    token = _build_msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    if "access_token" not in token:
        return "Login failed while acquiring token.", 400

    access_token = token["access_token"]
    claims = token.get("id_token_claims") or {}
    tid = claims.get("tid") or "unknown"

    me = requests.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if me.status_code != 200:
        return "Login failed while fetching profile.", 400

    profile = me.json()
    oid = profile.get("id")
    email = (profile.get("mail") or profile.get("userPrincipalName") or "").lower()
    name = profile.get("displayName") or ""

    if not _email_domain_allowed(email):
        return "Access not granted (domain not allowed).", 403

    subject = f"{tid}:{oid}" if tid and oid else None

    _ensure_csrf_token()

    # Identify / create user identity
    u = None
    if subject:
        u = get_user_by_subject(subject)
    if not u and email:
        u = get_user_by_email(email)

    if not u:
        # Invite-only: only create an identity if there's a valid invite waiting.
        # SUPER_ADMIN users should already exist via seeding.
        if has_valid_invite(email):
            u = create_user_if_missing(email)
        else:
            return redirect(FRONTEND_URL + "/?error=invalid_access")

    if subject and u and not u["provider_subject"]:
        attach_subject_to_user(email, subject)

    if not u or u["is_active"] != 1:
        return redirect(FRONTEND_URL + "/?error=invalid_access")

    user_id = int(u["id"])

    # Accept any pending invites (could be multiple orgs)
    accept_valid_invites_for_user(email, user_id)

    # Determine org memberships
    orgs = list_orgs_for_user(user_id)

    # Gate: only allow sign-in for users who are on a team or have SUPER_ADMIN system role.
    system_role = (u["system_role"] or "").upper()
    if system_role != "SUPER_ADMIN" and len(orgs) == 0:
        session.pop("user", None)
        return "Access not granted. You must be invited to a team.", 403

    active_org_id = None
    active_role = None

    # Prefer previously selected org if still valid
    prior_org_id = session.get("user", {}).get("orgId")
    if prior_org_id:
        m = get_membership(user_id, int(prior_org_id))
        if m and m["is_active"] == 1:
            active_org_id = int(prior_org_id)
            active_role = m["role"]

    # Auto-select if exactly one org
    if not active_org_id and len([o for o in orgs if o.get("is_active") == 1]) == 1:
        active_org_id = int(orgs[0]["id"])
        active_role = orgs[0]["role"]

    session["user"] = {
        "userId": user_id,
        "email": u["email"],
        "name": name,
        "subject": subject,
        "systemRole": u["system_role"],
        "orgId": active_org_id,
        "role": active_role,
    }

    return redirect(FRONTEND_URL + "/")


@app.post("/auth/logout")
@limiter.limit(os.getenv("RATE_LIMIT_LOGOUT", "30 per minute"))
def logout():
    session.clear()
    return jsonify({"ok": True})



@app.get("/api/me")
def api_me():
    if session.get("user"):
        _ensure_csrf_token()
        # Clear stale org context if org was deleted / DB reset
        _validate_active_org_membership()
    return jsonify(session.get("user"))



@app.get("/api/orgs")
@require_login
def api_orgs():
    u = session["user"]
    orgs = list_orgs_for_user(int(u["userId"]))
    return jsonify({"orgs": orgs, "activeOrgId": u.get("orgId")})


@app.post("/api/set-org")
@require_login
def api_set_org():
    if not request.is_json:
        return jsonify({"error": "expected_json"}), 400
    data = request.get_json(silent=True) or {}
    org_id = data.get("orgId")
    if not org_id:
        return jsonify({"error": "missing_orgId"}), 400
    ok = _set_active_org_for_user(int(session["user"]["userId"]), int(org_id))
    if not ok:
        return jsonify({"error": "not_a_member"}), 403
    return jsonify({"ok": True, "orgId": session["user"]["orgId"], "role": session["user"]["role"]})


# ----------------------------
# Org-scoped admin features
# ----------------------------
@app.get("/api/members")
@require_org_role("ADMIN")
def api_members():
    org_id = int(session["user"]["orgId"])
    members = list_members(org_id)
    org = get_org(org_id)
    used = count_active_members(org_id)
    return jsonify({"members": members, "seatLimit": org["seat_limit"], "seatsUsed": used})


@app.post("/api/invite")
@require_org_role("ADMIN")
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
    if role not in {"COACH", "SCOUT"}:
        return jsonify({"error": "invalid_role"}), 400

    org_id = int(session["user"]["orgId"])
    org = get_org(org_id)
    used = count_active_members(org_id)

    # Seat limit enforcement: only counts active memberships.
    # You can decide whether inviting an existing user counts immediately; here we only block
    # if they'd create/activate a membership beyond limit.
    if used >= int(org["seat_limit"]):
        return jsonify({"error": "seat_limit_reached", "seatLimit": org["seat_limit"], "seatsUsed": used}), 409

    inviter_user_id = int(session["user"]["userId"])
    result = create_invite(org_id=org_id, email=email, role=role, invited_by_user_id=inviter_user_id)
    return jsonify({"ok": True, "result": result, "seatLimit": org["seat_limit"], "seatsUsed": used})


@app.patch("/api/members/<int:target_user_id>/role")
@require_org_role("ADMIN")
def api_change_role(target_user_id: int):
    """Team admins may only change roles of non-admin members, and only to COACH/SCOUT.
    (Changing team admins is reserved for system SUPER_ADMINs.)
    """
    if not request.is_json:
        return jsonify({"error": "expected_json"}), 400

    org_id = int(session["user"]["orgId"])
    acting_user_id = int(session["user"]["userId"])

    if int(target_user_id) == acting_user_id:
        return jsonify({"error": "cannot_change_own_role"}), 409

    target = get_membership(user_id=int(target_user_id), org_id=org_id)
    if not target or target["is_active"] != 1:
        return jsonify({"error": "member_not_found"}), 404

    # Team admins cannot modify other admins (only system operators can change team admins)
    if (target["role"] or "").upper() == "ADMIN":
        return jsonify({"error": "cannot_modify_admin"}), 409

    data = request.get_json(silent=True) or {}
    new_role = (data.get("role") or "").strip().upper()
    if new_role not in {"COACH", "SCOUT"}:
        return jsonify({"error": "invalid_role"}), 400

    upsert_membership(org_id=org_id, user_id=int(target_user_id), role=new_role, is_active=1)
    return jsonify({"ok": True})



@app.delete("/api/members/<int:target_user_id>")
@require_org_role("ADMIN")
def api_remove_member(target_user_id: int):
    """Team admins may remove (deactivate) non-admin members only.
    Removing team admins is reserved for system SUPER_ADMINs.
    """
    org_id = int(session["user"]["orgId"])
    acting_user_id = int(session["user"]["userId"])

    if int(target_user_id) == acting_user_id:
        return jsonify({"error": "cannot_remove_self"}), 409

    target = get_membership(user_id=int(target_user_id), org_id=org_id)
    if not target or target["is_active"] != 1:
        return jsonify({"error": "member_not_found"}), 404

    if (target["role"] or "").upper() == "ADMIN":
        return jsonify({"error": "cannot_remove_admin"}), 409

    delete_membership(org_id=org_id, user_id=int(target_user_id))
    return jsonify({"ok": True})



# ----------------------------
# Hashmark operator endpoints
# ----------------------------
@app.get("/api/system/users")
@require_system_role("SUPER_ADMIN")
def api_system_users():
    return jsonify({"users": list_users_system()})


@app.post("/api/system/create-org-admin")
@require_system_role("SUPER_ADMIN")
def api_system_create_org_admin():
    """Hashmark operator flow:
    - create org
    - ensure admin user exists by email
    - grant membership ADMIN
    """
    if not request.is_json:
        return jsonify({"error": "expected_json"}), 400
    data = request.get_json(silent=True) or {}
    org_name = (data.get("orgName") or "").strip()
    admin_email = (data.get("adminEmail") or "").strip().lower()
    seat_limit = int(data.get("seatLimit") or DEFAULT_ORG_SEAT_LIMIT)

    if not org_name:
        return jsonify({"error": "missing_orgName"}), 400
    if not admin_email or "@" not in admin_email:
        return jsonify({"error": "invalid_email"}), 400

    org = create_org(org_name, seat_limit=seat_limit)
    admin_user = create_user_if_missing(admin_email)
    upsert_membership(org_id=int(org["id"]), user_id=int(admin_user["id"]), role="ADMIN", is_active=1)

    return jsonify({"ok": True, "orgId": int(org["id"]), "orgName": org["name"], "adminUserId": int(admin_user["id"])})




# ----------------------------
# System SUPER_ADMIN org management
# ----------------------------
@app.get("/api/system/orgs")
@require_system_role("SUPER_ADMIN")
def api_system_orgs():
    return jsonify({"orgs": list_orgs_system()})


@app.get("/api/system/orgs/<int:org_id>/members")
@require_system_role("SUPER_ADMIN")
def api_system_org_members(org_id: int):
    org = get_org(org_id)
    if not org:
        return jsonify({"error": "org_not_found"}), 404
    members = list_members(org_id)
    used = count_active_members(org_id)
    return jsonify({"org": dict(org), "members": members, "seatsUsed": used})


@app.put("/api/system/orgs/<int:org_id>/admin")
@require_system_role("SUPER_ADMIN")
def api_system_set_team_admin(org_id: int):
    """Change the TEAM ADMIN for an org. This is the only member-management
    operation system SUPER_ADMINs should perform (besides deleting the org).
    """
    if not request.is_json:
        return jsonify({"error": "expected_json"}), 400

    org = get_org(org_id)
    if not org:
        return jsonify({"error": "org_not_found"}), 404

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "invalid_email"}), 400

    user = create_user_if_missing(email)
    set_team_admin(org_id=org_id, new_admin_user_id=int(user["id"]))
    return jsonify({"ok": True, "orgId": org_id, "adminEmail": email})


@app.delete("/api/system/orgs/<int:org_id>")
@require_system_role("SUPER_ADMIN")
def api_system_delete_org(org_id: int):
    """Delete a team/org completely (cascades memberships + invites)."""
    ok = delete_org(org_id)
    if not ok:
        return jsonify({"error": "org_not_found"}), 404
    return jsonify({"ok": True})


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0").strip() == "1"
    app.run(port=5000, debug=debug)
