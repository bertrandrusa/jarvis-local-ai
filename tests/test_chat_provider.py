"""Tests for cloud/local chat-provider selection."""

import os
import unittest
from unittest.mock import patch

from core.chat_provider import _split_messages, provider_model, provider_name


class ChatProviderTests(unittest.TestCase):
    def test_api_key_automatically_selects_openai(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            self.assertEqual(provider_name(), "openai")

    def test_without_key_falls_back_to_ollama(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(provider_name(), "ollama")

    def test_explicit_provider_overrides_automatic_selection(self):
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "ollama", "OPENAI_API_KEY": "test-key"},
            clear=True,
        ):
            self.assertEqual(provider_name(), "ollama")

    def test_openai_model_can_be_overridden(self):
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "custom-model",
            },
            clear=True,
        ):
            self.assertEqual(provider_model("local-model"), "custom-model")

    def test_system_message_becomes_instructions(self):
        instructions, conversation = _split_messages(
            [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Good evening."},
            ]
        )
        self.assertEqual(instructions, "Be concise.")
        self.assertEqual(len(conversation), 2)


if __name__ == "__main__":
    unittest.main()
