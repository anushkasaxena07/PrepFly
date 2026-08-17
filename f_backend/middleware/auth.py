import os
import jwt
from functools import wraps
from flask import request, jsonify, g

def get_secret_key():
    return os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "c8fa4668d31b53d0b5dd4786fe27e2946a527436f95869970a5118bf48c6f342"

def verify_jwt_token(token):
    if not token:
        return None
    token_clean = token.strip()
    if token_clean.lower().startswith("bearer "):
        token_clean = token_clean[7:].strip()

    try:
        secret = get_secret_key()
        payload = jwt.decode(token_clean, secret, algorithms=["HS256"])
        return payload
    except Exception as e:
        print("[JWT VERIFY NOTICE]", e)
        return None

def get_supabase():
    import app
    return app.supabase

ACTIVE_USER_SESSIONS = {}

def set_active_session(user_id, session_id):
    if not user_id or not session_id:
        return
    ACTIVE_USER_SESSIONS[user_id] = session_id

def get_active_session(user_id):
    return ACTIVE_USER_SESSIONS.get(user_id)

def require_auth(roles=None, allow_optional=False):
    """
    Decorator for verifying JWT Bearer tokens and enforcing role & organization authorization.
    Attaches g.current_user, g.user_id, g.user_role, and g.organization_id to Flask's request context.
    Also enforces single active device session per user.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get("Authorization") or request.headers.get("X-Authorization")
            token_payload = verify_jwt_token(auth_header)

            if not token_payload:
                if allow_optional:
                    g.current_user = None
                    g.user_id = None
                    g.user_role = "candidate"
                    g.organization_id = "org_default"
                    return f(*args, **kwargs)
                return jsonify({"error": "Unauthorized: Missing or invalid JWT Bearer token", "code": "UNAUTHORIZED"}), 401

            user_id = token_payload.get("sub") or token_payload.get("user_id") or token_payload.get("id")
            token_role = token_payload.get("role", "candidate")
            token_org_id = token_payload.get("organization_id") or token_payload.get("org_id") or "org_default"
            token_session_id = token_payload.get("session_id")

            user_db = None
            if user_id and not user_id.startswith("sa_"):
                try:
                    supabase = get_supabase()
                    res = supabase.table("users").select("*").eq("id", user_id).execute()
                    if res and hasattr(res, "data") and res.data:
                        user_db = res.data[0]
                except Exception as e:
                    print("[AUTH USER LOOKUP NOTICE]", e)

            # Single device session validation
            if user_id:
                active_session = ACTIVE_USER_SESSIONS.get(user_id)
                if not active_session and user_db and isinstance(user_db, dict):
                    db_sess = user_db.get("current_session_id")
                    if db_sess:
                        active_session = db_sess
                        ACTIVE_USER_SESSIONS[user_id] = db_sess

                if active_session and token_session_id != active_session:
                    return jsonify({
                        "error": "You have been logged out because your account was logged in from another device.",
                        "code": "SESSION_SUPERSEEDED"
                    }), 401

            verified_role = (user_db.get("role") if user_db else token_role) or "candidate"
            verified_org_id = (user_db.get("organization_id") if user_db else token_org_id) or "org_default"

            # Normalize roles for matching (e.g. 'super_admin' vs 'SUPER_ADMIN')
            user_role_upper = str(verified_role).upper()
            
            if roles:
                allowed_roles_upper = [str(r).upper() for r in (roles if isinstance(roles, (list, tuple, set)) else [roles])]
                
                # Super Admin bypass for admin endpoints
                is_authorized = (user_role_upper in allowed_roles_upper) or ("SUPER_ADMIN" in user_role_upper) or (user_role_upper == "SUPER_ADMIN")
                
                if not is_authorized:
                    return jsonify({"error": f"Forbidden: Role '{verified_role}' does not have access to this resource", "code": "FORBIDDEN"}), 403

            g.current_user = user_db or {"id": user_id, "role": verified_role, "organization_id": verified_org_id}
            g.user_id = user_id
            g.user_role = verified_role
            g.organization_id = verified_org_id
            g.session_id = token_session_id

            return f(*args, **kwargs)
        return decorated
    return decorator
