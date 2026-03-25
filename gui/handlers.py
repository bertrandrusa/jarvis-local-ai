from PySide6.QtCore import QObject, Signal, QThread, QTimer
import json
import re

from config import RESPONDER_MODEL, OLLAMA_URL, MAX_HISTORY

# =========================
# LAZY IMPORTS (CRITICAL)
# =========================
http_session = None
tts = None
SentenceBuffer = None
history_manager = None
ensure_exclusive_qwen = None
ensure_qwen_loaded = None
mark_qwen_used = None
app_settings = None
function_executor = None


def lazy_imports():
    global http_session, tts, SentenceBuffer, history_manager
    global ensure_exclusive_qwen, ensure_qwen_loaded, mark_qwen_used
    global app_settings, function_executor

    if http_session is None:
        from core.llm import http_session as _http
        from core.tts import tts as _tts, SentenceBuffer as _sb
        from core.history import history_manager as _hm
        from core.model_manager import ensure_exclusive_qwen as _emq
        from core.model_persistence import ensure_qwen_loaded as _eql, mark_qwen_used as _mqu
        from core.settings_store import settings as _settings
        from core.function_executor import executor as _exec

        http_session = _http
        tts = _tts
        SentenceBuffer = _sb
        history_manager = _hm
        ensure_exclusive_qwen = _emq
        ensure_qwen_loaded = _eql
        mark_qwen_used = _mqu
        app_settings = _settings
        function_executor = _exec


# =========================
# WORKER
# =========================
class ChatWorker(QObject):
    thought_chunk = Signal(str)
    response_chunk = Signal(str)
    think_start = Signal(bool)
    think_end = Signal()
    simple_response = Signal(str)
    error = Signal(str)
    status = Signal(str)
    done = Signal()

    def __init__(self, user_text, messages, is_tts_enabled, session_id, stop_event):
        super().__init__()
        self.user_text = user_text
        self.messages = messages
        self.is_tts_enabled = is_tts_enabled
        self.session_id = session_id
        self.stop_event = stop_event

    def process(self):
        try:
            lazy_imports()

            payload = {
                "model": RESPONDER_MODEL,
                "messages": self.messages + [{"role": "user", "content": self.user_text}],
                "stream": True
            }

            buffer = SentenceBuffer()
            full = ""

            with http_session.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True) as r:
                for line in r.iter_lines():
                    if self.stop_event.is_set():
                        break
                    if not line:
                        continue

                    data = json.loads(line.decode())
                    msg = data.get("message", {})

                    if "content" in msg:
                        content = msg["content"]
                        full += content
                        self.response_chunk.emit(content)

                        if self.is_tts_enabled:
                            for s in buffer.add(content):
                                tts.queue_sentence(s)

            rem = buffer.flush()
            if rem and self.is_tts_enabled:
                tts.queue_sentence(rem)

            self.messages.append({"role": "assistant", "content": full})
            self.done.emit()

        except Exception as e:
            self.error.emit(str(e))


# =========================
# HANDLERS
# =========================
class ChatHandlers(QObject):
    def __init__(self, main_window):
        super().__init__(main_window)

        lazy_imports()  # 🔥 CRITICAL

        self.main_window = main_window
        self.messages = [
            {"role": "system", "content": "You are a fast, concise assistant."}
        ]

        self.is_tts_enabled = False
        self._thread = None
        self._worker = None
        self._stop_event = None

    def send_message(self, text: str):
        lazy_imports()

        text = text.strip()
        if not text:
            return

        self.main_window.add_message_bubble("user", text)

        import threading
        self._stop_event = threading.Event()

        self._thread = QThread()
        self._worker = ChatWorker(
            text,
            self.messages.copy(),
            self.is_tts_enabled,
            None,
            self._stop_event
        )

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.process)
        self._worker.response_chunk.connect(
            lambda t: self.main_window.add_message_bubble("assistant", t)
        )
        self._worker.done.connect(self._thread.quit)

        self._thread.start()

    def stop_generation(self):
        if self._stop_event:
            self._stop_event.set()

    def toggle_tts(self, enabled: bool):
        lazy_imports()
        self.is_tts_enabled = enabled
        tts.toggle(enabled)