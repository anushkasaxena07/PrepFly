import re
from io import BytesIO
from gtts import gTTS
from services.speech_engine import extract_fillers, detect_pauses, calculate_pace_consistency, compute_speech_metrics

def generate_tts_audio_buffer(text: str) -> BytesIO:
    """Generates gTTS audio MP3 stream buffer for given text."""
    clean_text = re.sub(r'```[\s\S]*?```', '', text)
    clean_text = re.sub(r'`[^`]*`', '', clean_text)
    clean_text = re.sub(r'[#*_\-~>#]', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    if not clean_text:
        clean_text = "Here is the next question for your interview."
    
    if len(clean_text) > 1000:
        clean_text = clean_text[:1000]

    tts = gTTS(text=clean_text, lang="en", slow=False)
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf

__all__ = [
    "extract_fillers",
    "detect_pauses",
    "calculate_pace_consistency",
    "compute_speech_metrics",
    "generate_tts_audio_buffer"
]
