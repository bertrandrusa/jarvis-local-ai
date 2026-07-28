"""Secure API-key storage backed by the operating system credential vault."""

from __future__ import annotations

import os
from typing import Any

SERVICE_NAME = "JARVIS Local AI"
OPENAI_ACCOUNT = "openai-api-key"


def _keyring() -> Any:
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError(
            "Secure credential storage is unavailable. "
            "Run: pip install -r requirements.txt"
        ) from exc
    return keyring


def get_openai_api_key() -> str:
    """Return an environment key first, then the securely stored desktop key."""
    environment_key = os.getenv("OPENAI_API_KEY", "").strip()
    if environment_key:
        return environment_key
    try:
        return (_keyring().get_password(SERVICE_NAME, OPENAI_ACCOUNT) or "").strip()
    except Exception:
        return ""


def save_openai_api_key(api_key: str) -> None:
    """Validate and store an OpenAI project key in the OS credential vault."""
    cleaned = api_key.strip()
    if not cleaned:
        raise ValueError("Enter an API key before saving.")
    if not cleaned.startswith("sk-"):
        raise ValueError("This does not look like an OpenAI API key.")
    _keyring().set_password(SERVICE_NAME, OPENAI_ACCOUNT, cleaned)


def delete_openai_api_key() -> bool:
    """Delete the stored key. Environment-provided keys are not modified."""
    keyring = _keyring()
    try:
        keyring.delete_password(SERVICE_NAME, OPENAI_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        return False
    return True


def has_openai_api_key() -> bool:
    return bool(get_openai_api_key())
