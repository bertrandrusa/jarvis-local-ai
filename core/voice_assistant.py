"""
Voice Assistant - Optimized for fast local voice interaction.
Pipeline: STT → (optional web search) → LLM → TTS
"""

import threading
import json
from typing import Optional
try:
    from PySide6.QtCore import QObject, Signal
except:
    # fallback for non-UI init
    class QObject:
        pass

    class Signal:
        def __init__(self, *args, **kwargs):
            pass

        def emit(self, *args, **kwargs):
            pass

from config import (
    RESPONDER_MODEL, OLLAMA_URL, MAX_HISTORY, GRAY, RESET, CYAN, GREEN, WAKE_WORD
)

from core.stt import STTListener
from core.llm import http_session
from core.chat_provider import JARVIS_SYSTEM_PROMPT, stream_chat
from core.ollama import trim_messages
from core.tts import tts, SentenceBuffer
from core.function_executor import executor as function_executor


class VoiceAssistant(QObject):
    """Lightweight voice assistant."""

    wake_word_detected = Signal()
    speech_recognized = Signal(str)
    processing_started = Signal()
    processing_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.stt_listener: Optional[STTListener] = None
        self.running = False

        self.messages = [
            {
                "role": "system",
                "content": JARVIS_SYSTEM_PROMPT,
            }
        ]

    # ========================
    # INIT / START / STOP
    # ========================

    def initialize(self) -> bool:
        try:
            print(f"{CYAN}[VoiceAssistant] Initializing...{RESET}")

            self.stt_listener = STTListener(
                wake_word_callback=self._on_wake_word,
                speech_callback=self._on_speech
            )

            if not self.stt_listener.initialize():
                print(f"{GRAY}STT init failed{RESET}")
                return False

            if not tts.piper_exe:
                tts.initialize()

            print(f"{GREEN}✓ Ready{RESET}")
            return True

        except Exception as e:
            print(f"{GRAY}Init error: {e}{RESET}")
            return False

    def start(self):
        if self.running:
            return

        if not self.stt_listener and not self.initialize():
            return

        self.running = True
        self.stt_listener.start()

        print(f"{CYAN}Say '{GREEN}{WAKE_WORD}{CYAN}' to start{RESET}")

    def stop(self):
        if not self.running:
            return

        self.running = False
        if self.stt_listener:
            self.stt_listener.stop()

        print(f"{GRAY}Stopped{RESET}")

    # ========================
    # EVENTS
    # ========================

    def _on_wake_word(self):
        print(f"{GREEN}Wake word detected{RESET}")
        self.wake_word_detected.emit()

    def _on_speech(self, text: str):
        if not text.strip():
            return

        text = text.lower().replace("jarvis", "").strip()
        if not text:
            return

        self.speech_recognized.emit(text)
        self.processing_started.emit()

        print(f"{CYAN}User: {text}{RESET}")

        threading.Thread(
            target=self._process_query,
            args=(text,),
            daemon=True
        ).start()

    # ========================
    # CORE PIPELINE
    # ========================

    def _process_query(self, user_text: str):
        try:
            # 🔍 OPTIONAL: detect web search intent (simple, fast)
            if user_text.startswith("search") or "search for" in user_text:
                query = user_text.replace("search for", "", 1).strip()
                result = function_executor.execute("web_search", {"query": query})
                context = json.dumps(result.get("data", {}), ensure_ascii=False)
                self._generate_response(f"{context}\n\nUser: {user_text}")
            else:
                self._generate_response(user_text)

        except Exception as e:
            print(f"{GRAY}Error: {e}{RESET}")
            self.error_occurred.emit(str(e))
            self.processing_finished.emit()

    # ========================
    # LLM RESPONSE
    # ========================

    def _generate_response(self, prompt: str):
        try:
            # Trim history
            self.messages = trim_messages(self.messages, MAX_HISTORY)

            self.messages.append({"role": "user", "content": prompt})

            sentence_buffer = SentenceBuffer()
            full_response = ""

            for content in stream_chat(
                self.messages,
                ollama_model=RESPONDER_MODEL,
                ollama_url=OLLAMA_URL,
                session=http_session,
            ):
                full_response += content
                for sentence in sentence_buffer.add(content):
                    tts.queue_sentence(sentence)

            # flush remaining
            rem = sentence_buffer.flush()
            if rem:
                tts.queue_sentence(rem)

            self.messages.append({"role": "assistant", "content": full_response})

            print(f"{GREEN}Assistant: {full_response}{RESET}")
            self.processing_finished.emit()

        except Exception as e:
            print(f"{GRAY}LLM error: {e}{RESET}")
            self.processing_finished.emit()


# Global instance
voice_assistant = VoiceAssistant()
