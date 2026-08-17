import os
import re
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

from services.gemini import chat_model, flash_model, pro_model
from services.logging_config import setup_logging_and_sentry, check_health

load_dotenv()

app = Flask(__name__)
setup_logging_and_sentry(app)

app.chat_model = chat_model
app.flash_model = flash_model
app.pro_model = pro_model

# ─── Supabase PostgreSQL Client Setup ──────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    import logging
    logging.warning("SUPABASE_URL or SUPABASE_KEY is missing from environment variables (.env).")

_raw_supabase: Client = create_client(SUPABASE_URL or "https://atfozkznxxuehyjgqvvm.supabase.co", SUPABASE_KEY or "sb_publishable_B1hsywJt3jKSDdij-3iddw_ZNStwZWY")

class SupabasePostgreSQLClient:
    def __init__(self, raw_client):
        self._raw_client = raw_client

    @property
    def storage(self):
        return self._raw_client.storage

    def table(self, table_name):
        builder = self._raw_client.table(table_name)
        
        class TableQueryWrapper:
            def __init__(self, table_name, builder):
                self.table_name = table_name
                self.builder = builder

            def insert(self, json_data, **kwargs):
                data = self._clean_data(json_data)
                return TableQueryWrapper(self.table_name, self.builder.insert(data, **kwargs))

            def update(self, json_data, **kwargs):
                data = self._clean_data(json_data)
                return TableQueryWrapper(self.table_name, self.builder.update(data, **kwargs))

            def upsert(self, json_data, **kwargs):
                data = self._clean_data(json_data)
                return TableQueryWrapper(self.table_name, self.builder.upsert(data, **kwargs))

            def _clean_data(self, data):
                if self.table_name == "sessions":
                    import json
                    metadata_fields = ["category", "difficulty", "stage", "ats_score", "structured_resume", "final_score_100", "grade_color", "grade_label", "performance_level", "hiring_recommendation"]
                    
                    def process_dict(d):
                        if not isinstance(d, dict):
                            return d
                        d_copy = dict(d)
                        metadata = {}
                        for field in metadata_fields:
                            if field in d_copy:
                                metadata[field] = d_copy.pop(field)
                        if metadata:
                            existing_meta = {}
                            if "storage_path" in d_copy and d_copy["storage_path"]:
                                try:
                                    existing_meta = json.loads(d_copy["storage_path"])
                                    if not isinstance(existing_meta, dict):
                                        existing_meta = {}
                                except Exception:
                                    pass
                            existing_meta.update(metadata)
                            d_copy["storage_path"] = json.dumps(existing_meta)
                        return d_copy

                    if isinstance(data, dict):
                        return process_dict(data)
                    elif isinstance(data, list):
                        return [process_dict(x) for x in data]
                return data

            def execute(self, retries=3, backoff_sec=0.2):
                last_err = None
                for attempt in range(retries):
                    try:
                        res = self.builder.execute()
                        if self.table_name == "sessions" and hasattr(res, "data") and res.data:
                            import json
                            metadata_fields = ["category", "difficulty", "stage", "ats_score", "structured_resume", "final_score_100", "grade_color", "grade_label", "performance_level", "hiring_recommendation"]
                            for row in res.data:
                                if isinstance(row, dict) and "storage_path" in row and row["storage_path"]:
                                    try:
                                        meta = json.loads(row["storage_path"])
                                        if isinstance(meta, dict):
                                            for field in metadata_fields:
                                                if field in meta and field not in row:
                                                    row[field] = meta[field]
                                    except Exception:
                                        pass
                        return res
                    except Exception as err:
                        last_err = err
                        err_msg = str(err)
                        if "PGRST204" in err_msg or "PGRST205" in err_msg or "schema cache" in err_msg or "Could not find" in err_msg:
                            import logging
                            logging.warning(f"[DB SCHEMA NOTICE] Table {self.table_name} query notice: {err_msg}")
                            raise err
                        import logging, time
                        logging.warning(f"[DB RETRY {attempt+1}/{retries}] Table {self.table_name} query notice: {err}")
                        if attempt < retries - 1:
                            time.sleep(backoff_sec * (attempt + 1))
                import logging
                logging.error(f"[DB ERROR] Table {self.table_name} query failed after {retries} retries: {last_err}")
                raise last_err

            def __getattr__(self, name):
                attr = getattr(self.builder, name)
                if callable(attr):
                    def method(*args, **kwargs):
                        ret = attr(*args, **kwargs)
                        if hasattr(ret, "execute"):
                            return TableQueryWrapper(self.table_name, ret)
                        return ret
                    return method
                return attr

        return TableQueryWrapper(table_name, builder)

supabase = SupabasePostgreSQLClient(_raw_supabase)

def upload_to_supabase_storage(bucket_name: str, file_input, destination_filename: str, content_type: str = None) -> str:
    """Uploads file bytes directly to Supabase Storage bucket and returns public URL."""
    if not content_type:
        import mimetypes
        content_type, _ = mimetypes.guess_type(destination_filename)
        content_type = content_type or "application/octet-stream"

    if isinstance(file_input, bytes):
        file_bytes = file_input
    elif hasattr(file_input, "read"):
        file_input.seek(0)
        file_bytes = file_input.read()
    elif isinstance(file_input, str) and os.path.exists(file_input):
        with open(file_input, "rb") as f:
            file_bytes = f.read()
    else:
        file_bytes = str(file_input).encode("utf-8")

    base_url = SUPABASE_URL.rstrip("/")
    public_url = f"{base_url}/storage/v1/object/public/{bucket_name}/{destination_filename}"

    try:
        supabase.storage.from_(bucket_name).upload(
            destination_filename,
            file_bytes,
            file_options={"upsert": "true", "content-type": content_type}
        )
    except Exception as upload_err:
        print(f"[SUPABASE STORAGE NOTICE] Bucket '{bucket_name}' upload notice: {upload_err}")
        try:
            supabase.storage.create_bucket(bucket_name, options={"public": True})
            supabase.storage.from_(bucket_name).upload(
                destination_filename,
                file_bytes,
                file_options={"upsert": "true", "content-type": content_type}
            )
        except Exception:
            pass

    return public_url

# ─── Upload Folder Configuration ────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ─── Register Blueprints ────────────────────────────────────────────────────────
from routes.auth import auth_bp
from routes.interview import interview_bp
from routes.coding import coding_bp
from routes.resume import resume_bp
from routes.admin import admin_bp
from payment import payment_bp
from subscription import subscription_bp
from invoice import invoice_bp
from webhook import webhook_bp

app.register_blueprint(auth_bp)
app.register_blueprint(interview_bp)
app.register_blueprint(coding_bp)
app.register_blueprint(resume_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(subscription_bp)
app.register_blueprint(invoice_bp)
app.register_blueprint(webhook_bp)
from middleware.limiter import limiter
limiter.init_app(app)

# ─── CORS Setup ─────────────────────────────────────────────────────────────────
allowed_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "https://prepfly.vercel.app",
    re.compile(r"^https://.*\.vercel\.app$")
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

CORS(app, resources={r"/*": {
    "origins": allowed_origins,
    "supports_credentials": True,
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "X-Super-Admin", "X-User-Role", "X-Role", "X-Organization-Id"]
}})

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin") or "*"
        res = Response("", status=200)
        res.headers["Access-Control-Allow-Origin"] = origin
        res.headers["Access-Control-Allow-Credentials"] = "true"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, X-Super-Admin, X-User-Role, X-Role, X-Organization-Id"
        res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        res.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
        return res

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin") or "*"
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, X-Super-Admin, X-User-Role, X-Role, X-Organization-Id"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
    return response

@app.route("/<path:dummy>", methods=["OPTIONS"])
@app.route("/", methods=["OPTIONS"])
def handle_global_options(dummy=None):
    origin = request.headers.get("Origin") or "*"
    res = Response("", status=200)
    res.headers["Access-Control-Allow-Origin"] = origin
    res.headers["Access-Control-Allow-Credentials"] = "true"
    res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, X-Super-Admin, X-User-Role, X-Role, X-Organization-Id"
    res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    res.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
    return res

@app.route("/health", methods=["GET", "HEAD"])
@app.route("/system/health", methods=["GET", "HEAD"])
@app.route("/api/system/health", methods=["GET", "HEAD"])
def health_check():
    try:
        health_data, _ = check_health(supabase)
    except Exception:
        health_data = {"status": "online"}
    health_data["status"] = "healthy"
    return jsonify(health_data), 200

@app.route("/ready", methods=["GET", "HEAD"])
@app.route("/system/ready", methods=["GET", "HEAD"])
@app.route("/api/system/ready", methods=["GET", "HEAD"])
def readiness_check():
    health_data, status_code = check_health(supabase)
    is_ready = (status_code == 200)
    return jsonify({
        "status": "ready" if is_ready else "not_ready",
        "ready": is_ready,
        "timestamp": health_data.get("timestamp")
    }), (200 if is_ready else 503)

@app.route("/notifications", methods=["GET"])
@app.route("/api/notifications", methods=["GET"])
def get_user_notifications():
    import datetime
    user_id = request.args.get("user_id", "me")
    org_id = request.args.get("org_id", "global")
    try:
        res = supabase.table("announcements").select("*").execute()
        announcements = res.data if (res and hasattr(res, "data") and res.data) else []
        notifications = []
        for a in announcements:
            notifications.append({
                "id": a.get("id") or a.get("announcement_id"),
                "title": a.get("title", "Announcement"),
                "message": a.get("message") or a.get("content", ""),
                "time": a.get("created_at") or "Recently",
                "read": False
            })
        if not notifications:
            notifications = [{
                "id": "notif_welcome",
                "title": "Welcome to PrepFly!",
                "message": "Start your AI Mock Interview or practice coding challenges today.",
                "time": datetime.datetime.utcnow().isoformat(),
                "read": False
            }]
        return jsonify({"notifications": notifications}), 200
    except Exception as e:
        return jsonify({"notifications": []}), 200

@app.route("/debug-sentry", methods=["GET"])
@app.route("/api/debug-sentry", methods=["GET"])
def trigger_sentry_test_error():
    """Triggers a intentional ZeroDivisionError exception to verify Sentry event capture."""
    division_by_zero = 1 / 0
    return jsonify({"result": division_by_zero}), 200

@app.errorhandler(Exception)
def handle_global_exception(e):
    origin = request.headers.get("Origin") or "*"
    import logging
    logging.exception(f"Global server error: {e}")
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except Exception:
        pass
    res = jsonify({"error": str(e)})
    res.status_code = 500
    res.headers["Access-Control-Allow-Origin"] = origin
    res.headers["Access-Control-Allow-Credentials"] = "true"
    res.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, X-Super-Admin, X-Organization-Id"
    res.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return res

if __name__ == "__main__":
    port_str = os.getenv("PORT", "5000").strip()
    port_num = int(port_str) if port_str.isdigit() else 5000
    app.run(host="0.0.0.0", port=port_num, debug=False)