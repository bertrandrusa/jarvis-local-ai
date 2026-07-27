"""
LLM interaction - optimized for fast local responses.
Handles direct communication with Ollama.
"""

import requests

from config import RESPONDER_MODEL, OLLAMA_URL, GRAY, RESET
from core.ollama import ollama_api_url

# Persistent session (VERY IMPORTANT for speed)
http_session = requests.Session()


# =========================
# SIMPLE CHAT CALL
# =========================

def chat(messages, stream=True, max_tokens=120):
    """
    Send chat request to Ollama.
    
    Args:
        messages: conversation history
        stream: stream response or not
        max_tokens: limit response length (speed boost)
    """
    try:
        payload = {
            "model": RESPONDER_MODEL,
            "messages": messages,
            "stream": stream,
            "keep_alive": "3m",
            "options": {
                "num_predict": max_tokens,   # 🔥 LIMIT TOKENS = FASTER
                "temperature": 0.7
            }
        }

        response = http_session.post(
            ollama_api_url(OLLAMA_URL, "chat"),
            json=payload,
            stream=stream,
            timeout=60
        )

        response.raise_for_status()
        return response

    except Exception as e:
        print(f"{GRAY}[LLM ERROR: {e}]{RESET}")
        return None


# =========================
# FAST NON-STREAM OPTION
# =========================

def quick_chat(prompt: str):
    """
    Fast single-shot response (no streaming).
    Useful for short replies.
    """
    try:
        payload = {
            "model": RESPONDER_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "3m",
            "options": {
                "num_predict": 80   # shorter = faster
            }
        }

        response = http_session.post(
            ollama_api_url(OLLAMA_URL, "generate"),
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        return data.get("response", "")

    except Exception as e:
        print(f"{GRAY}[LLM QUICK ERROR: {e}]{RESET}")
        return ""


# =========================
# LIGHT PRELOAD (OPTIONAL)
# =========================

def preload_model():
    """
    Warm up the model for faster first response.
    """
    try:
        print(f"{GRAY}[LLM] Preloading model...{RESET}")

        http_session.post(
            ollama_api_url(OLLAMA_URL, "generate"),
            json={
                "model": RESPONDER_MODEL,
                "prompt": "hi",
                "stream": False,
                "keep_alive": "10m",
                "options": {"num_predict": 1}
            },
            timeout=60
        )

        print(f"{GRAY}[LLM] Model ready.{RESET}")

    except Exception as e:
        print(f"{GRAY}[LLM preload failed: {e}]{RESET}")
