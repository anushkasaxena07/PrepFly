from flask import Blueprint, request, jsonify
from services.webhook_service import handle_razorpay_webhook, handle_system_notification_webhook

webhook_bp = Blueprint("webhook_bp", __name__)

@webhook_bp.route("/api/webhook/razorpay", methods=["POST"])
@webhook_bp.route("/webhook/razorpay", methods=["POST"])
def api_razorpay_webhook():
    try:
        raw_body = request.get_data()
        signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
        
        result = handle_razorpay_webhook(raw_body, signature)
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print("Webhook error:", e)
        return jsonify({"error": str(e)}), 500

@webhook_bp.route("/api/webhook/notifications", methods=["POST"])
@webhook_bp.route("/webhook/notifications", methods=["POST"])
def api_system_notification_webhook():
    """
    Webhook endpoint allowing external services or SuperAdmin to dispatch real-time system notifications.
    Triggers instant Supabase Realtime WebSocket push to all online React dashboards.
    """
    try:
        raw_body = request.get_data()
        signature = request.headers.get("X-System-Signature") or request.headers.get("x-system-signature") or request.headers.get("X-Signature")
        
        result = handle_system_notification_webhook(raw_body, signature)
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print("System notification webhook error:", e)
        return jsonify({"error": str(e)}), 500
