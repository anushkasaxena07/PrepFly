from flask import Blueprint, request, jsonify
from services.payment_service import create_razorpay_order, verify_razorpay_payment, ALLOWED_PLAN_AMOUNTS

payment_bp = Blueprint("payment_bp", __name__)

def get_supabase():
    try:
        import app
        return app.supabase
    except Exception:
        from local_supabase import SQLiteSupabaseMock
        return SQLiteSupabaseMock()

@payment_bp.route("/api/payment/create-order", methods=["POST"])
@payment_bp.route("/payment/create-order", methods=["POST"])
def api_create_order():
    try:
        from app import _get_optional_user
        p = _get_optional_user()
        data = request.get_json() or {}
        requested_org = data.get("organization_id") or data.get("org_id") or data.get("user_id") or "org_default"
        plan_id = data.get("plan_id")
        amount = data.get("amount")

        if p and p.get("role") != "SUPER_ADMIN":
            token_org = p.get("organization_id")
            if token_org and requested_org != "org_default" and str(requested_org) != str(token_org):
                return jsonify({"error": "Forbidden: Cannot create orders for another organization"}), 403

        org_id = requested_org if (p and p.get("role") == "SUPER_ADMIN") else ((p.get("organization_id") if p and p.get("organization_id") else requested_org) or "org_default")
        result = create_razorpay_order(org_id=org_id, plan_id=plan_id, amount_inr=amount)
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print("Create order error:", e)
        return jsonify({"error": "Failed to create payment order"}), 500

@payment_bp.route("/api/payment/verify", methods=["POST"])
@payment_bp.route("/payment/verify", methods=["POST"])
def api_verify_payment():
    try:
        data = request.get_json() or {}
        org_id = data.get("organization_id") or data.get("org_id") or data.get("user_id") or "org_default"
        razorpay_order_id = data.get("razorpay_order_id") or data.get("order_id")
        razorpay_payment_id = data.get("razorpay_payment_id") or data.get("payment_id")
        razorpay_signature = data.get("razorpay_signature") or data.get("signature")
        plan_id = data.get("plan_id")
        amount = data.get("amount")

        result = verify_razorpay_payment(
            org_id=org_id,
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            plan_id=plan_id,
            amount_inr=amount
        )
        return jsonify(result), 200
    except ValueError as ve:
        return jsonify({"error": str(ve), "status": "FAILED"}), 400
    except Exception as e:
        print("Verify payment error:", e)
        return jsonify({"error": "Payment verification failed"}), 500

@payment_bp.route("/api/payment/record-failed", methods=["POST"])
@payment_bp.route("/payment/record-failed", methods=["POST"])
def api_record_failed():
    try:
        from services.payment_service import record_failed_payment
        data = request.get_json() or {}
        org_id = data.get("organization_id") or data.get("org_id") or data.get("user_id") or "org_default"
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        reason = data.get("reason", "Payment failed or cancelled by user")
        
        result = record_failed_payment(org_id, razorpay_order_id, razorpay_payment_id, reason)
        return jsonify(result), 200
    except Exception as e:
        print("Record failed error:", e)
        return jsonify({"error": str(e)}), 400

@payment_bp.route("/api/payment/history", methods=["GET"])
@payment_bp.route("/payment/history", methods=["GET"])
def api_payment_history():
    try:
        from app import _get_optional_user
        p = _get_optional_user()
        requested_org = request.args.get("organization_id") or request.args.get("org_id") or request.args.get("user_id") or "org_default"
        
        if p and p.get("role") != "SUPER_ADMIN":
            token_org = p.get("organization_id")
            if token_org and requested_org != "org_default" and str(requested_org) != str(token_org):
                return jsonify({"error": "Forbidden: Cannot access payment history of another organization"}), 403

        org_id = requested_org if (p and p.get("role") == "SUPER_ADMIN") else ((p.get("organization_id") if p and p.get("organization_id") else requested_org) or "org_default")
        supabase = get_supabase()
        res = supabase.table("payment").select("*").eq("organization_id", org_id).execute()
        rows = res.data if res and hasattr(res, "data") and res.data else []

        history = []
        for r in rows:
            history.append({
                "id": r.get("id"),
                "organization_id": r.get("organization_id"),
                "razorpay_order_id": r.get("razorpay_order_id"),
                "razorpay_payment_id": r.get("razorpay_payment_id"),
                "amount": r.get("amount"),
                "currency": r.get("currency") or "INR",
                "invoice_number": r.get("invoice_number"),
                "invoice_id": r.get("id"),
                "status": r.get("status") or "Success",
                "payment_method": r.get("payment_method") or "Razorpay (UPI / Card)",
                "created_at": r.get("created_at")
            })
        return jsonify(history), 200
    except Exception as e:
        print("Fetch payment history error:", e)
        return jsonify([]), 200
