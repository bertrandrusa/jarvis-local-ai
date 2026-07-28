"""Controllers for chat generation, local history, and session management."""

import threading

from PySide6.QtCore import QObject, QThread, Signal

from config import MAX_HISTORY, RESPONDER_MODEL
from core.chat_provider import JARVIS_SYSTEM_PROMPT
from core.ollama import trim_messages

SYSTEM_MESSAGE = {
    "role": "system",
    "content": JARVIS_SYSTEM_PROMPT,
}


class ChatWorker(QObject):
    """Stream one provider response without blocking the Qt event loop."""

    response_chunk = Signal(str)
    completed = Signal(str)
    error = Signal(str)
    status = Signal(str)
    done = Signal()

    def __init__(self, messages, is_tts_enabled, stop_event):
        super().__init__()
        self.messages = messages
        self.is_tts_enabled = is_tts_enabled
        self.stop_event = stop_event

    def process(self):
        try:
            from core.llm import http_session
            from core.chat_provider import (
                provider_model,
                provider_name,
                stream_chat,
            )
            from core.settings_store import settings
            from core.tts import SentenceBuffer, tts

            model = settings.get("models.chat", RESPONDER_MODEL)
            base_url = settings.get("ollama_url", "http://localhost:11434")

            sentence_buffer = SentenceBuffer()
            full_response = ""
            provider = provider_name()
            active_model = provider_model(model)
            location = "OpenAI" if provider == "openai" else "local Ollama"
            self.status.emit(f"Generating with {location} · {active_model}…")

            for content in stream_chat(
                self.messages,
                ollama_model=model,
                ollama_url=base_url,
                session=http_session,
            ):
                if self.stop_event.is_set():
                    self.status.emit("Generation stopped")
                    break

                full_response += content
                self.response_chunk.emit(content)

                if self.is_tts_enabled:
                    for sentence in sentence_buffer.add(content):
                        tts.queue_sentence(sentence)

            remainder = sentence_buffer.flush()
            if remainder and self.is_tts_enabled and not self.stop_event.is_set():
                tts.queue_sentence(remainder)

            if full_response:
                self.completed.emit(full_response)
        except Exception as exc:  # noqa: BLE001 - report worker failures to the UI
            self.error.emit(str(exc))
        finally:
            self.done.emit()


class ChatHandlers(QObject):
    """Coordinate the chat UI, provider worker, and SQLite history."""

    def __init__(self, main_window):
        super().__init__(main_window)
        from core.history import history_manager

        self.main_window = main_window
        self.history_manager = history_manager
        self.current_session_id = None
        self.is_tts_enabled = False

        self._thread = None
        self._worker = None
        self._stop_event = None
        self._response_bubble = None

    def initialize_sessions(self):
        sessions = self.history_manager.get_sessions()
        if sessions:
            self.select_session(sessions[0]["id"])
        else:
            self.new_chat()

    def new_chat(self):
        self.current_session_id = self.history_manager.create_session()
        self.main_window.clear_chat_display()
        self.main_window.chat_tab.refresh_sidebar(self.current_session_id)
        self.main_window.set_status("Ready")

    def select_session(self, session_id: str):
        self.current_session_id = session_id
        self.main_window.clear_chat_display()
        for message in self.history_manager.get_messages(session_id):
            self.main_window.add_message_bubble(
                message["role"],
                message["content"],
            )
        self.main_window.chat_tab.refresh_sidebar(session_id)
        self.main_window.set_status("Ready")

    def toggle_session_pin(self, session_id: str):
        self.history_manager.toggle_pin(session_id)
        self.main_window.chat_tab.refresh_sidebar(self.current_session_id)

    def rename_session(self, session_id: str, title: str):
        self.history_manager.update_session_title(session_id, title)
        self.main_window.chat_tab.refresh_sidebar(self.current_session_id)

    def delete_session(self, session_id: str):
        self.history_manager.delete_session(session_id)
        if session_id == self.current_session_id:
            sessions = self.history_manager.get_sessions()
            if sessions:
                self.select_session(sessions[0]["id"])
            else:
                self.new_chat()
        else:
            self.main_window.chat_tab.refresh_sidebar(self.current_session_id)

    def send_message(self, text: str):
        from core.settings_store import settings

        text = text.strip()
        if not text or self._thread:
            return
        if not self.current_session_id:
            self.new_chat()

        existing_messages = self.history_manager.get_messages(self.current_session_id)
        self.history_manager.add_message(self.current_session_id, "user", text)
        if not existing_messages:
            title = text if len(text) <= 48 else f"{text[:45]}…"
            self.history_manager.update_session_title(self.current_session_id, title)

        self.main_window.add_message_bubble("user", text)
        self.main_window.chat_tab.clear_input()
        self.main_window.chat_tab.set_generating_state(True)
        self.main_window.chat_tab.refresh_sidebar(self.current_session_id)
        self._response_bubble = self.main_window.add_message_bubble("assistant", "")

        max_history = int(settings.get("general.max_history", MAX_HISTORY))
        conversation = self.history_manager.get_messages(self.current_session_id)
        messages = trim_messages([SYSTEM_MESSAGE, *conversation], max_history + 1)

        self._stop_event = threading.Event()
        self._thread = QThread(self)
        self._worker = ChatWorker(
            messages=messages,
            is_tts_enabled=self.is_tts_enabled,
            stop_event=self._stop_event,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.process)
        self._worker.response_chunk.connect(self._append_response)
        self._worker.completed.connect(self._save_response)
        self._worker.error.connect(self._show_error)
        self._worker.status.connect(self.main_window.set_status)
        self._worker.done.connect(self._thread.quit)
        self._worker.done.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._finish_generation)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _append_response(self, text: str):
        if self._response_bubble:
            self._response_bubble.append_text(text)
            self.main_window.chat_tab.scroll_to_bottom()

    def _save_response(self, text: str):
        if self.current_session_id and text:
            self.history_manager.add_message(
                self.current_session_id,
                "assistant",
                text,
            )
            if self._response_bubble:
                self._response_bubble.set_text(text)

    def _show_error(self, error: str):
        message = (
            "JARVIS could not reach the configured AI provider. If you are using "
            "OpenAI, confirm that OPENAI_API_KEY is set and your computer is "
            "online. If you are using Ollama, confirm that its server and model "
            f"are available.\n\nDetails: {error}"
        )
        if self._response_bubble:
            self._response_bubble.set_text(message)
        self.main_window.set_status("Connection error")

    def _finish_generation(self):
        self.main_window.chat_tab.set_generating_state(False)
        if self.main_window.chat_tab.status_label.text() != "Connection error":
            self.main_window.set_status("Ready")
        self._thread = None
        self._worker = None
        self._stop_event = None
        self._response_bubble = None

    def stop_generation(self):
        if self._stop_event:
            self._stop_event.set()

    def toggle_tts(self, enabled: bool):
        from core.tts import tts

        self.is_tts_enabled = enabled
        tts.toggle(enabled)
