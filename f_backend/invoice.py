from flask import Blueprint, jsonify, make_response, send_file
from services.invoice_service import get_invoice_html
from io import BytesIO

invoice_bp = Blueprint("invoice_bp", __name__)

@invoice_bp.route("/api/invoice/<invoice_id>", methods=["GET"])
@invoice_bp.route("/invoice/<invoice_id>", methods=["GET"])
def api_get_invoice(invoice_id):
    try:
        html_content, code = get_invoice_html(invoice_id)
        if code != 200:
            return jsonify({"error": "Invoice not found"}), 404
        
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html"
        return response
    except Exception as e:
        print("Get invoice error:", e)
        return jsonify({"error": str(e)}), 500

@invoice_bp.route("/api/invoice/download/<invoice_id>", methods=["GET"])
@invoice_bp.route("/invoice/download/<invoice_id>", methods=["GET"])
def api_download_invoice(invoice_id):
    try:
        html_content, code = get_invoice_html(invoice_id)
        if code != 200:
            return jsonify({"error": "Invoice not found"}), 404

        buffer = BytesIO()
        buffer.write(html_content.encode("utf-8"))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Invoice_{invoice_id}.html",
            mimetype="text/html"
        )
    except Exception as e:
        print("Download invoice error:", e)
        return jsonify({"error": str(e)}), 500
