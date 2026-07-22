from flask import Blueprint, request, jsonify
from services.webhook_service import handle_razorpay_webhook

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
