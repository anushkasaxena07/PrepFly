import os
import math
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("interviewsystem.embeddings")

from services.gemini import get_api_key_pool

_embeddings_client = None

def get_embeddings_client():
    """Initializes and caches GoogleGenerativeAIEmbeddings client using dedicated Embeddings API keys."""
    global _embeddings_client
    if _embeddings_client is not None:
        return _embeddings_client

    api_keys = get_api_key_pool(domain="embeddings")
    embedding_models = ["models/embedding-001", "embedding-001", "text-embedding-004"]
    
    for key in api_keys:
        for m in embedding_models:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                client = GoogleGenerativeAIEmbeddings(model=m, google_api_key=key)
                _embeddings_client = client
                logger.info(f"Initialized Google Generative AI Embeddings model: '{m}' with key ({key[:8]}...)")
                return _embeddings_client
            except Exception as e:
                logger.warning(f"Could not initialize embedding model '{m}' with key ({key[:8]}...): {e}")
                
    return None

def fallback_vector_embedding(text: str, dim: int = 128) -> List[float]:
    """Fallback deterministic n-gram vector embedding generator when API is uncontactable."""
    import hashlib
    text_clean = (text or "").lower().strip()
    words = [w.strip("?,.()\"'") for w in text_clean.split() if w]
    
    vec = [0.0] * dim
    if not words:
        return vec
        
    for idx, w in enumerate(words):
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        pos = h % dim
        val = ((h >> 8) % 100) / 100.0
        vec[pos] += val + (1.0 / (idx + 1))
        
    # Normalize vector to unit length
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

def generate_embedding(text: str) -> List[float]:
    """Generates vector embedding for input text using Google AI Embeddings or fallback vectorizer."""
    if not text or not text.strip():
        return [0.0] * 128
        
    text_sample = text.strip()[:2000]
    client = get_embeddings_client()
    
    if client:
        try:
            emb = client.embed_query(text_sample)
            if isinstance(emb, list) and len(emb) > 0:
                return emb
        except Exception as err:
            logger.warning(f"Google AI Embedding API call failed: {err}. Using local vector fallback.")
            
    return fallback_vector_embedding(text_sample)

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        # Truncate/pad to minimum length if dimension mismatch
        min_len = min(len(vec_a or []), len(vec_b or []))
        if min_len == 0:
            return 0.0
        vec_a = vec_a[:min_len]
        vec_b = vec_b[:min_len]

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)

def chunk_text(text: str, max_words: int = 100) -> List[str]:
    """Splits long text into manageable semantic context chunks."""
    if not text or not text.strip():
        return []
        
    lines = text.strip().split("\n")
    chunks = []
    current_chunk = []
    current_word_count = 0
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        words = line_clean.split()
        if current_word_count + len(words) > max_words and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = words
            current_word_count = len(words)
        else:
            current_chunk.extend(words)
            current_word_count += len(words)
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def retrieve_grounded_context(query_text: str, raw_context: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    RAG Retrieval Engine:
    1. Chunks context into semantic fragments.
    2. Embeds query & context fragments into vector representations.
    3. Ranks fragments by Cosine Similarity.
    4. Returns Top-K most semantically relevant factual snippets.
    """
    if not query_text or not raw_context:
        return []

    chunks = chunk_text(raw_context)
    if not chunks:
        return []

    query_vec = generate_embedding(query_text)
    
    results = []
    for idx, chunk in enumerate(chunks):
        chunk_vec = generate_embedding(chunk)
        sim = cosine_similarity(query_vec, chunk_vec)
        results.append({
            "chunk_index": idx,
            "text": chunk,
            "similarity_score": round(sim, 4)
        })

    # Sort descending by cosine similarity score
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:top_k]

def build_grounded_prompt(system_mandate: str, query_text: str, context_text: str, top_k: int = 3) -> str:
    """
    Assembles a grounded anti-hallucination prompt incorporating retrieved RAG vector context.
    """
    retrieved_items = retrieve_grounded_context(query_text, context_text, top_k=top_k)
    
    if retrieved_items:
        retrieved_text_block = "\n".join([f"- [Relevance: {item['similarity_score'] * 100:.1f}%] {item['text']}" for item in retrieved_items])
    else:
        retrieved_text_block = context_text[:1500] if context_text else "No background resume context provided."

    grounded_prompt = f"""{system_mandate}

STRICT ANTI-HALLUCINATION MANDATE:
- Base your response EXCLUSIVELY on the retrieved factual context below.
- Do NOT invent, assume, or fabricate experience, tools, projects, or metrics not present in the context.
- If a detail is missing from the retrieved context, acknowledge that it is unspecified rather than guessing.

RETRIEVED FACTUAL CONTEXT (Vector Similarity Ranked):
{retrieved_text_block}

USER PROMPT / TASK:
{query_text}"""

    return grounded_prompt
