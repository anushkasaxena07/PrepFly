import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tasks.celery_app import celery_app
from services.ats import parse_resume_content, calculate_ats_match
from services.pdf_service import generate_pdf_html_report
from services.speech import generate_tts_audio_buffer

def get_supabase():
    import app
    return app.supabase

def upload_storage(bucket_name, file_input, filename, content_type=None):
    import app
    return app.upload_to_supabase_storage(bucket_name, file_input, filename, content_type)

@celery_app.task(name="tasks.async_send_email")
def async_send_email(recipient_email, subject, body, purpose="notification"):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_email = os.getenv("SMTP_EMAIL", "saxenaanushka9645@gmail.com")
    smtp_password = os.getenv("SMTP_PASSWORD", "dytfawgfpxnxmqtp")
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        logging.info(f"[CELERY EMAIL TASK] Successfully sent {purpose} email to {recipient_email}")
        return {"status": "sent", "recipient": recipient_email}
    except Exception as e:
        logging.error(f"[CELERY EMAIL TASK FAILED] {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="tasks.async_parse_resume_and_ats")
def async_parse_resume_and_ats(session_id, resume_text, job_description=""):
    try:
        from services.gemini import pro_model
        parse_result = parse_resume_content(resume_text, pro_model)
        ats_info = calculate_ats_match(resume_text, job_description) if job_description else {}
        ats_score = parse_result.get("ats_score", 70)

        supabase = get_supabase()
        supabase.table("sessions").update({
            "ats_score": ats_score,
            "structured_resume": parse_result.get("structured_data", {})
        }).eq("session_id", session_id).execute()

        logging.info(f"[CELERY ATS TASK] Successfully processed resume for session {session_id}")
        return {
            "session_id": session_id,
            "ats_score": ats_score,
            "structured_data": parse_result.get("structured_data", {})
        }
    except Exception as e:
        logging.error(f"[CELERY ATS TASK FAILED] {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="tasks.async_generate_pdf_report")
def async_generate_pdf_report(candidate_name, candidate_email, session_id, overall_score, grade, feedbacks):
    try:
        html_report = generate_pdf_html_report(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            date_str=None,
            overall_score=overall_score,
            grade=grade,
            feedbacks=feedbacks,
            final_report_markdown="PrepFly Comprehensive Interview Evaluation Report"
        )
        report_filename = f"report_{session_id}.html"
        public_url = upload_storage("reports", html_report.encode("utf-8"), report_filename, "text/html")

        supabase = get_supabase()
        supabase.table("sessions").update({"final_report": public_url}).eq("session_id", session_id).execute()

        logging.info(f"[CELERY PDF TASK] Report generated and uploaded to {public_url}")
        return {"session_id": session_id, "report_url": public_url}
    except Exception as e:
        logging.error(f"[CELERY PDF TASK FAILED] {e}")
        return {"status": "error", "error": str(e)}

@celery_app.task(name="tasks.async_generate_tts")
def async_generate_tts(text, filename="speech.mp3"):
    try:
        buf = generate_tts_audio_buffer(text)
        audio_url = upload_storage("audio", buf.getvalue(), filename, "audio/mpeg")
        logging.info(f"[CELERY TTS TASK] Audio synthesized and uploaded to {audio_url}")
        return {"audio_url": audio_url}
    except Exception as e:
        logging.error(f"[CELERY TTS TASK FAILED] {e}")
        return {"status": "error", "error": str(e)}
