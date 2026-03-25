"""
Minimal App - Fast, Clean, No Extra Features
"""

import threading
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF
)

from config import VOICE_ASSISTANT_ENABLED
from gui.styles import AURA_STYLESHEET 


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        print("A: window base init")

        self.setWindowTitle("JARVIS (Lite)")
        print("B: title set")

        self.resize(1100, 750)
        print("C: resize done")

        self.setStyleSheet(AURA_STYLESHEET)
        print("D: stylesheet applied")

        # STEP BY STEP LOAD
        print("E: importing handlers")
        from gui.handlers import ChatHandlers

        print("F: creating handlers")
        self.handlers = ChatHandlers(self)

        print("G: importing tabs")
        from gui.tabs.chat import ChatTab
        from gui.tabs.settings import SettingsTab

        print("H: creating chat tab")
        self.chat_tab = ChatTab()

        print("I: creating settings tab")
        self.settings_tab = SettingsTab()

        print("J: adding UI")
        self.addSubInterface(self.chat_tab, FIF.CHAT, "Chat")
        self.addSubInterface(self.settings_tab, FIF.SETTING, "Settings")

        print("K: connect signals")
        self._connect_signals()

        print("L: init voice")
        self._init_voice_assistant()

    print("M: DONE INIT")
    # =========================
    # VOICE ASSISTANT
    # =========================
    def _init_voice_assistant(self):
        if not VOICE_ASSISTANT_ENABLED:
            return

        def init_va():
            # 🔥 lazy import
            from core.voice_assistant import voice_assistant
            from core.tts import tts

            if voice_assistant.initialize():
                tts.toggle(True)
                voice_assistant.start()

        threading.Thread(target=init_va, daemon=True).start()

    # =========================
    # SIGNALS
    # =========================
    def _connect_signals(self):
        self.chat_tab.send_message_requested.connect(self._on_send)
        self.chat_tab.stop_generation_requested.connect(self.handlers.stop_generation)
        self.chat_tab.tts_toggled.connect(self.handlers.toggle_tts)

    def _on_send(self, text):
        self.handlers.send_message(text)

    # =========================
    # UI HELPERS
    # =========================
    def set_status(self, text):
        self.chat_tab.set_status(text)

    def add_message_bubble(self, role, text, is_thinking=False):
        self.chat_tab.add_message_bubble(role, text, is_thinking)

    def clear_chat_display(self):
        self.chat_tab.clear_chat_display()


def create_app():
    return MainWindow()