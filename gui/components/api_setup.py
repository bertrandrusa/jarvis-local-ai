"""First-run OpenAI API-key setup dialog."""

from PySide6.QtWidgets import QLabel, QLineEdit
from qfluentwidgets import LineEdit, MessageBoxBase, SubtitleLabel

from core.credentials import save_openai_api_key


class ApiKeySetupDialog(MessageBoxBase):
    """Collect and securely store an API key without exposing it in settings files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title_label = SubtitleLabel("Connect JARVIS to OpenAI", self)
        self.description_label = QLabel(
            "Enter a new OpenAI API key. It will be stored in Windows "
            "Credential Manager—not in this project or its settings file.",
            self,
        )
        self.description_label.setWordWrap(True)

        self.key_input = LineEdit(self)
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-proj-…")
        self.key_input.setMinimumWidth(420)

        self.error_label = QLabel("", self)
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #ff6b6b;")

        self.viewLayout.addWidget(self.title_label)
        self.viewLayout.addWidget(self.description_label)
        self.viewLayout.addWidget(self.key_input)
        self.viewLayout.addWidget(self.error_label)

        self.yesButton.setText("Save securely")
        self.cancelButton.setText("Use Ollama")
        self.widget.setMinimumWidth(500)

    def validate(self) -> bool:
        try:
            save_openai_api_key(self.key_input.text())
        except Exception as exc:
            self.error_label.setText(str(exc))
            return False
        return True
