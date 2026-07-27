import unittest

from core.ollama import normalize_ollama_url, ollama_api_url, trim_messages


class OllamaHelpersTests(unittest.TestCase):
    def test_normalizes_host_and_api_urls(self):
        self.assertEqual(
            normalize_ollama_url("http://localhost:11434/api/"),
            "http://localhost:11434",
        )
        self.assertEqual(
            normalize_ollama_url("http://localhost:11434"),
            "http://localhost:11434",
        )

    def test_builds_each_endpoint_once(self):
        self.assertEqual(
            ollama_api_url("http://localhost:11434/api", "/api/chat"),
            "http://localhost:11434/api/chat",
        )

    def test_trims_history_without_losing_system_message(self):
        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "user", "content": "three"},
        ]
        self.assertEqual(
            trim_messages(messages, 3),
            [messages[0], messages[2], messages[3]],
        )


if __name__ == "__main__":
    unittest.main()
