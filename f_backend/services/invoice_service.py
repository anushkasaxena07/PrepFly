import uuid
from datetime import datetime

def get_supabase():
    import app
    return app.supabase

def generate_invoice(org_id, payment_id, amount=500.0):
    supabase = get_supabase()
    inv_id = f"inv_{uuid.uuid4().hex[:8]}"
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    gst_amount = round(amount * 0.18, 2)
    created_at = datetime.utcnow().isoformat()

    try:
        supabase.table("invoice").insert({
            "id": inv_id,
            "payment_id": payment_id,
            "organization_id": org_id,
            "invoice_number": invoice_number,
            "amount": amount,
            "gst": gst_amount,
            "created_at": created_at
        }).execute()
    except Exception as e:
        print("Generate invoice notice:", e)

    return {
        "id": inv_id,
        "payment_id": payment_id,
        "organization_id": org_id,
        "invoice_number": invoice_number,
        "amount": amount,
        "gst": gst_amount,
        "total_amount": round(amount + gst_amount, 2),
        "created_at": created_at
    }

def get_invoice_html(invoice_id):
    supabase = get_supabase()
    res = supabase.table("invoice").select("*").or_(f"id.eq.{invoice_id},invoice_number.eq.{invoice_id}").execute()
    inv = res.data[0] if (res and hasattr(res, "data") and res.data) else None

    if not inv:
        return "<h1>Invoice Not Found</h1>", 404

    org_res = supabase.table("organization").select("*").eq("id", inv.get("organization_id", "")).execute()
    org = org_res.data[0] if (org_res and hasattr(org_res, "data") and org_res.data) else {}

    pay_res = supabase.table("payment").select("*").eq("id", inv.get("payment_id", "")).execute()
    pay = pay_res.data[0] if (pay_res and hasattr(pay_res, "data") and pay_res.data) else {}

    amount = float(inv.get("amount", 500.0))
    gst = float(inv.get("gst", 90.0))
    total = amount + gst

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice {inv.get('invoice_number')}</title>
        <style>
            body {{ font-family: 'Inter', sans-serif; background: #080c14; color: #fff; padding: 40px; }}
            .card {{ max-width: 650px; margin: 0 auto; background: #0c1220; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 32px; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }}
            .header {{ display: flex; justify-space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px; margin-bottom: 20px; }}
            .logo {{ font-size: 24px; font-weight: 900; color: #00f0c8; }}
            .title {{ font-size: 18px; font-weight: 700; color: #a0aec0; text-align: right; }}
            .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
            .lbl {{ font-size: 11px; text-transform: uppercase; color: #718096; font-weight: 700; }}
            .val {{ font-size: 14px; color: #e2e8f0; font-weight: 600; margin-top: 4px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ text-align: left; padding: 12px; font-size: 12px; color: #a0aec0; border-bottom: 1px solid rgba(255,255,255,0.1); }}
            td {{ padding: 12px; font-size: 14px; color: #edf2f7; border-bottom: 1px solid rgba(255,255,255,0.05); }}
            .total-row {{ font-weight: 800; font-size: 16px; color: #00f0c8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <div class="logo">PrepFly Enterprise</div>
                <div class="title">OFFICIAL INVOICE</div>
            </div>
            <div class="meta-grid">
                <div>
                    <div class="lbl">Billed To</div>
                    <div class="val">{org.get('name', 'Organization Admin')}</div>
                    <div class="val" style="color: #a0aec0; font-weight:400;">{org.get('email', 'admin@organization.edu')}</div>
                </div>
                <div>
                    <div class="lbl">Invoice Info</div>
                    <div class="val">Invoice #: {inv.get('invoice_number')}</div>
                    <div class="val">Date: {str(inv.get('created_at'))[:10]}</div>
                    <div class="val">Payment ID: {pay.get('razorpay_payment_id', 'N/A')}</div>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Description</th>
                        <th>Qty</th>
                        <th style="text-align:right;">Amount (INR)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>1-Year Unlimited Annual Enterprise Subscription</td>
                        <td>1</td>
                        <td style="text-align:right;">₹{amount:.2f}</td>
                    </tr>
                    <tr>
                        <td>GST (18% Statutory Rate)</td>
                        <td>1</td>
                        <td style="text-align:right;">₹{gst:.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td colspan="2">Total Amount Paid</td>
                        <td style="text-align:right;">₹{total:.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return html, 200
