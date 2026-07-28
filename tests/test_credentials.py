"""Tests for secure API credential handling without a real OS keyring."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.credentials import (
    OPENAI_ACCOUNT,
    SERVICE_NAME,
    delete_openai_api_key,
    get_openai_api_key,
    save_openai_api_key,
)


class PasswordDeleteError(Exception):
    pass


class FakeKeyring:
    def __init__(self):
        self.values = {}
        self.errors = SimpleNamespace(PasswordDeleteError=PasswordDeleteError)

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, password):
        self.values[(service, account)] = password

    def delete_password(self, service, account):
        key = (service, account)
        if key not in self.values:
            raise PasswordDeleteError
        del self.values[key]


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.keyring = FakeKeyring()
        self.module_patch = patch.dict(sys.modules, {"keyring": self.keyring})
        self.module_patch.start()

    def tearDown(self):
        self.module_patch.stop()

    def test_saved_key_round_trip(self):
        with patch.dict(os.environ, {}, clear=True):
            save_openai_api_key("sk-proj-test")
            self.assertEqual(get_openai_api_key(), "sk-proj-test")
            self.assertTrue(delete_openai_api_key())
            self.assertEqual(get_openai_api_key(), "")

    def test_environment_key_has_priority(self):
        self.keyring.set_password(SERVICE_NAME, OPENAI_ACCOUNT, "sk-stored")
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "sk-environment"},
            clear=True,
        ):
            self.assertEqual(get_openai_api_key(), "sk-environment")

    def test_rejects_invalid_key_shape(self):
        with self.assertRaises(ValueError):
            save_openai_api_key("not-an-api-key")


if __name__ == "__main__":
    unittest.main()
