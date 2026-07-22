from flask import Blueprint, request, jsonify
from services.subscription_service import get_org_subscription_status, block_if_expired

subscription_bp = Blueprint("subscription_bp", __name__)

@subscription_bp.route("/api/subscription/status", methods=["GET"])
@subscription_bp.route("/subscription/status", methods=["GET"])
@subscription_bp.route("/api/subscription", methods=["GET"])
@subscription_bp.route("/subscription", methods=["GET"])
def api_subscription_status():
    try:
        org_id = request.args.get("organization_id") or request.args.get("org_id") or request.args.get("user_id") or "org_default"
        status = get_org_subscription_status(org_id)
        return jsonify(status), 200
    except Exception as e:
        print("Subscription status error:", e)
        return jsonify({"error": str(e)}), 500

@subscription_bp.route("/api/subscription/check-access", methods=["GET"])
@subscription_bp.route("/subscription/check-access", methods=["GET"])
def api_check_access():
    try:
        org_id = request.args.get("organization_id") or request.args.get("org_id") or request.args.get("user_id") or "org_default"
        is_blocked = block_if_expired(org_id)
        return jsonify({
            "organization_id": org_id,
            "access_allowed": not is_blocked,
            "is_blocked": is_blocked,
            "message": "Your organization's trial or subscription has expired. Renew your subscription to continue." if is_blocked else "Access granted."
        }), 200
    except Exception as e:
        return jsonify({"access_allowed": False, "is_blocked": True, "error": str(e)}), 500
