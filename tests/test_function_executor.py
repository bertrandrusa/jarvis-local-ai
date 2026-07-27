import sys
import types
import unittest

from core.function_executor import FunctionExecutor


class FakeDDGS:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def text(self, query, max_results=5):
        self.query = query
        return [
            {
                "title": "Local AI",
                "body": "A useful result about private assistants.",
                "href": "https://example.com/local-ai",
            }
        ][:max_results]


class FunctionExecutorTests(unittest.TestCase):
    def setUp(self):
        self.previous_module = sys.modules.get("duckduckgo_search")
        fake_module = types.ModuleType("duckduckgo_search")
        fake_module.DDGS = FakeDDGS
        sys.modules["duckduckgo_search"] = fake_module
        self.executor = FunctionExecutor()

    def tearDown(self):
        if self.previous_module is None:
            sys.modules.pop("duckduckgo_search", None)
        else:
            sys.modules["duckduckgo_search"] = self.previous_module

    def test_web_search_returns_structured_results(self):
        result = self.executor.execute("web_search", {"query": "local AI"})

        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["query"], "local AI")
        self.assertEqual(
            result["data"]["results"][0]["url"],
            "https://example.com/local-ai",
        )

    def test_empty_web_search_is_rejected(self):
        result = self.executor.execute("web_search", {"query": "  "})
        self.assertFalse(result["success"])

    def test_unknown_function_is_rejected(self):
        result = self.executor.execute("missing", {})
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
