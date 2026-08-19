import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("interviewsystem.ai_failover")

DEFAULT_FALLBACK_KEY = "AIzaSyBYSdXjmLnimrFY7ujWfRDIwyk_8cm9Ywo"

# Domain-specific API Key Mapping
DOMAIN_KEY_MAP = {
    "interview": ["GEMINI_INTERVIEW_KEY", "GEMINI_LIVE_INTERVIEW_KEY"],
    "report": ["GEMINI_REPORT_KEY", "GEMINI_PRO_KEY", "GEMINI_ATS_KEY"],
    "coding": ["GEMINI_CODING_KEY", "GEMINI_CODE_KEY"],
    "embeddings": ["GEMINI_EMBEDDINGS_KEY", "GEMINI_EMBED_KEY"]
}

def get_api_key_pool(domain: str = None):
    """
    Builds prioritized list of active & backup Gemini API keys for a specific functional domain.
    Ensures key isolation across features (Interviews, Reports, Coding, Embeddings).
    """
    keys = []
    
    # 1. Domain-Specific Dedicated API Key
    if domain and domain in DOMAIN_KEY_MAP:
        for env_var in DOMAIN_KEY_MAP[domain]:
            val = os.getenv(env_var)
            if val and val not in keys:
                keys.append(val)
                logger.debug(f"Assigned dedicated key for domain '{domain}': {env_var}")
                break

    # 2. Shared Primary API Key
    primary_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_KEY")
    if primary_key and primary_key not in keys:
        keys.append(primary_key)
        
    # 3. Emergency Backup Key Pool
    backup_keys = [
        os.getenv("BACKUP_GEMINI_API_KEY"),
        os.getenv("GEMINI_API_KEY_BACKUP"),
        os.getenv("GEMINI_API_KEY_FALLBACK"),
        os.getenv("GOOGLE_API_KEY_BACKUP")
    ]
    for bk in backup_keys:
        if bk and bk not in keys:
            keys.append(bk)
            
    if not keys:
        keys.append(DEFAULT_FALLBACK_KEY)
        
    return keys

class ResilientInterviewAIModel:
    """
    Resilient AI Model Wrapper for Live Interviews & Feature Domains:
    - Dedicated Key Isolation: Uses domain-specific API keys for live interviews, reports, coding, and embeddings.
    - Automatic Failover: Rotates across API Key pool and model candidates upon encountering
      rate limits (429), quota errors, or model deprecations.
    """
    def __init__(self, domain: str = "interview", model_candidates=None, temperature: float = 0.5):
        self.domain = domain
        self.model_candidates = model_candidates or [
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro"
        ]
        self.temperature = temperature

    def invoke(self, input_messages, config=None, **kwargs):
        api_keys = get_api_key_pool(domain=self.domain)
        last_exception = None

        # Outer Loop: Model Candidates (Fastest first)
        for model_name in self.model_candidates:
            # Inner Loop: API Key Failover Pool (Dedicated Key -> Primary Key -> Backup Key)
            for key_idx, api_key in enumerate(api_keys):
                try:
                    llm = ChatGoogleGenerativeAI(
                        api_key=api_key,
                        model=model_name,
                        temperature=self.temperature
                    )
                    response = llm.invoke(input_messages, config=config, **kwargs)
                    
                    # Ensure string format for response content
                    if hasattr(response, "content") and isinstance(response.content, list):
                        text_parts = []
                        for part in response.content:
                            if isinstance(part, str):
                                text_parts.append(part)
                            elif isinstance(part, dict) and "text" in part:
                                text_parts.append(part["text"])
                        response.content = "".join(text_parts)

                    if key_idx > 0 or model_name != self.model_candidates[0]:
                        logger.info(f"⚡ Live Failover [{self.domain}] successful! Used Key #{key_idx+1} ({api_key[:8]}...) with Model '{model_name}'.")

                    return response
                except Exception as err:
                    last_exception = err
                    logger.warning(
                        f"⚠️ AI Failover Notice [{self.domain}]: Model '{model_name}' with Key #{key_idx+1} failed ({type(err).__name__}). Trying next backup key/model candidate..."
                    )

        logger.error(f"❌ All AI API Keys and Model Candidates exhausted for domain '{self.domain}'. Last error: {last_exception}")
        raise last_exception or RuntimeError(f"All AI models and backup API keys exhausted for domain '{self.domain}'.")

def get_flash_model(temperature: float = 0.6, domain: str = "interview"):
    """Phase 12: Live Interview Model (Resilient Gemini Flash with Dedicated Key)."""
    return ResilientInterviewAIModel(
        domain=domain,
        model_candidates=["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
        temperature=temperature
    )

def get_pro_model(temperature: float = 0.4, domain: str = "report"):
    """Phase 12: Final Report Model (Resilient Gemini Pro with Dedicated Key)."""
    return ResilientInterviewAIModel(
        domain=domain,
        model_candidates=["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
        temperature=temperature
    )

def get_coding_model(temperature: float = 0.3, domain: str = "coding"):
    """Dedicated Model for Coding Assessment Reviews and AI Hints."""
    return ResilientInterviewAIModel(
        domain=domain,
        model_candidates=["gemini-1.5-flash", "gemini-2.0-flash"],
        temperature=temperature
    )

# Instantiate model singletons with dedicated domain allocation
flash_model = get_flash_model(domain="interview")
pro_model = get_pro_model(domain="report")
coding_model = get_coding_model(domain="coding")

# Backward compatibility alias
chat_model = flash_model
get_chat_model = get_flash_model
