"""Main JARVIS desktop window and feature navigation."""

import threading

from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow

from config import VOICE_ASSISTANT_ENABLED
from gui.styles import AURA_STYLESHEET


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS Local AI")
        self.resize(1280, 820)
        self.setStyleSheet(AURA_STYLESHEET)

        from gui.handlers import ChatHandlers
        from gui.tabs.briefing import BriefingView
        from gui.tabs.browser import BrowserTab
        from gui.tabs.chat import ChatTab
        from gui.tabs.dashboard import DashboardView
        from gui.tabs.home_automation import HomeAutomationTab
        from gui.tabs.planner import PlannerTab
        from gui.tabs.settings import SettingsTab

        self.dashboard_tab = DashboardView()
        self.chat_tab = ChatTab()
        self.planner_tab = PlannerTab()
        self.briefing_tab = BriefingView()
        self.home_tab = HomeAutomationTab()
        self.browser_tab = BrowserTab()
        self.settings_tab = SettingsTab()

        self.handlers = ChatHandlers(self)

        self.addSubInterface(self.dashboard_tab, FIF.HOME, "Dashboard")
        self.addSubInterface(self.chat_tab, FIF.CHAT, "Chat")
        self.addSubInterface(self.planner_tab, FIF.CALENDAR, "Planner")
        self.addSubInterface(self.briefing_tab, FIF.DOCUMENT, "Briefing")
        self.addSubInterface(self.home_tab, FIF.IOT, "Smart Home")
        self.addSubInterface(self.browser_tab, FIF.GLOBE, "Browser Agent")
        self.addSubInterface(self.settings_tab, FIF.SETTING, "Settings")

        self._connect_signals()
        self.handlers.initialize_sessions()
        self._init_voice_assistant()

    def _init_voice_assistant(self):
        if not VOICE_ASSISTANT_ENABLED:
            return

        def initialize():
            from core.tts import tts
            from core.voice_assistant import voice_assistant

            if voice_assistant.initialize():
                tts.toggle(True)
                voice_assistant.start()

        threading.Thread(target=initialize, daemon=True).start()

    def _connect_signals(self):
        self.chat_tab.send_message_requested.connect(self.handlers.send_message)
        self.chat_tab.stop_generation_requested.connect(self.handlers.stop_generation)
        self.chat_tab.tts_toggled.connect(self.handlers.toggle_tts)
        self.chat_tab.new_chat_requested.connect(self.handlers.new_chat)
        self.chat_tab.session_selected.connect(self.handlers.select_session)
        self.chat_tab.session_pin_requested.connect(self.handlers.toggle_session_pin)
        self.chat_tab.session_rename_requested.connect(self.handlers.rename_session)
        self.chat_tab.session_delete_requested.connect(self.handlers.delete_session)
        self.dashboard_tab.navigate_to.connect(self._navigate_from_dashboard)

    def _navigate_from_dashboard(self, route_key: str):
        destinations = {
            "plannerInterface": self.planner_tab,
            "homeInterface": self.home_tab,
            "briefingInterface": self.briefing_tab,
        }
        destination = destinations.get(route_key)
        if destination:
            self.switchTo(destination)

    def set_status(self, text):
        self.chat_tab.set_status(text)

    def add_message_bubble(self, role, text, is_thinking=False):
        return self.chat_tab.add_message_bubble(role, text, is_thinking)

    def clear_chat_display(self):
        self.chat_tab.clear_chat_display()


def create_app():
    return MainWindow()
