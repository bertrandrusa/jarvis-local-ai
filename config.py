"""Centralized defaults for JARVIS Local AI."""

# --- Model Configuration ---
# Use a lighter Ollama model for faster voice responses and lower GPU use
RESPONDER_MODEL = "qwen3:1.7b"
OLLAMA_URL = "http://localhost:11434"
MAX_HISTORY = 10

# Router disabled for performance; use simple handling instead
LOCAL_ROUTER_PATH = None
HF_ROUTER_REPO = None

# --- TTS Configuration ---
TTS_VOICE_MODEL = "en_GB-northern_english_male-medium"
TTS_MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx"
TTS_CONFIG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json"

# --- STT Configuration ---
STT_MODEL_PATH = None
STT_USE_WHISPER = False
WHISPER_MODEL_SIZE = "tiny"

WAKE_WORD_DETECTION_METHOD = "transcription"
REALTIMESTT_MODEL = "tiny"
USE_PORCUPINE_WAKE_WORD = False
PORCUPINE_ACCESS_KEY = None

WAKE_WORD = "jarvis"
WAKE_WORD_SENSITIVITY = 0.4
WAKE_WORD_CONFIRMATION_COUNT = 1
STT_SAMPLE_RATE = 16000
STT_CHUNK_SIZE = 4096
STT_RECORD_TIMEOUT = 4.0

# --- Voice Assistant Configuration ---
VOICE_ASSISTANT_ENABLED = True
QWEN_TIMEOUT_SECONDS = 180
QWEN_KEEP_ALIVE = "3m"

# --- Function Definitions ---
# Keep only what you still want in the assistant
FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "passthrough",
            "description": (
                "Default fallback for greetings, chitchat, general questions, "
                "conversation, and anything that does not require a tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "thinking": {
                        "type": "boolean",
                        "description": "True for complex reasoning, false for simple conversation."
                    }
                },
                "required": ["thinking"]
            }
        }
    }
]

# --- Console Colors ---
GRAY = "\033[90m"
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
