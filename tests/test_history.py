import os
import tempfile
import unittest

from core.history import ChatHistoryManager


class TestChatHistory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "history.db")
        self.mgr = ChatHistoryManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_session(self):
        sid = self.mgr.create_session("Test Session")
        self.assertIsNotNone(sid)
        sessions = self.mgr.get_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["title"], "Test Session")

    def test_add_message(self):
        sid = self.mgr.create_session("Chat 1")
        self.mgr.add_message(sid, "user", "Hello")
        self.mgr.add_message(sid, "assistant", "Hi there")

        msgs = self.mgr.get_messages(sid)
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]["content"], "Hello")
        self.assertEqual(msgs[1]["content"], "Hi there")

    def test_session_ordering(self):
        sid1 = self.mgr.create_session("Old")
        self.mgr.create_session("New")

        # New should be first
        sessions = self.mgr.get_sessions()
        self.assertEqual(sessions[0]["title"], "New")

        # Update Old
        self.mgr.add_message(sid1, "user", "bump")
        sessions = self.mgr.get_sessions()
        self.assertEqual(sessions[0]["title"], "Old")


if __name__ == "__main__":
    unittest.main()
