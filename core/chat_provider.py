"""Chat-provider selection and streaming for OpenAI or local Ollama."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

from core.credentials import get_openai_api_key

DEFAULT_OPENAI_MODEL = "gpt-5.6"
_ENV_LOADED = False
JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, Bertrand's sophisticated digital assistant. "
    "Speak with calm, polished British formality and address Bertrand as "
    "'sir' when natural. Be concise, intelligent, observant, and composed. "
    "Use occasional dry wit and understated humour, especially when warning "
    "about risky or inefficient choices, but never insult or become hostile. "
    "Prioritize Bertrand's safety, privacy, time, and long-term goals. "
    "Explain serious risks clearly and never let humour hide an important "
    "warning. Do not quote or imitate dialogue from films. Give clear, useful "
    "answers and say when you are uncertain."
)


def _load_environment() -> None:
    """Load .env when python-dotenv is installed, without making tests depend on it."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv()
    _ENV_LOADED = True


def provider_name() -> str:
    """Return the configured provider, automatically preferring OpenAI with a key."""
    _load_environment()
    configured = os.getenv("AI_PROVIDER", "").strip().lower()
    if not configured:
        try:
            from core.settings_store import settings
        except ImportError:
            configured = ""
        else:
            configured = str(settings.get("ai.provider", "")).strip().lower()
            if configured in {"automatic", "auto"}:
                configured = ""
    if configured:
        if configured not in {"openai", "ollama"}:
            raise ValueError("AI_PROVIDER must be either 'openai' or 'ollama'.")
        return configured
    return "openai" if get_openai_api_key() else "ollama"


def provider_model(ollama_model: str) -> str:
    if provider_name() == "openai":
        environment_model = os.getenv("OPENAI_MODEL", "").strip()
        if environment_model:
            return environment_model
        try:
            from core.settings_store import settings
        except ImportError:
            return DEFAULT_OPENAI_MODEL
        return str(settings.get("ai.openai_model", DEFAULT_OPENAI_MODEL)).strip()
    return ollama_model


def _split_messages(
    messages: list[dict[str, str]],
) -> tuple[str, list[dict[str, str]]]:
    instructions = "\n\n".join(
        message["content"]
        for message in messages
        if message.get("role") == "system" and message.get("content")
    )
    conversation = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]
    return instructions, conversation


def _openai_stream(messages: list[dict[str, str]]) -> Iterator[str]:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "An OpenAI API key is missing. Add one in JARVIS Settings → AI Provider."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI package is not installed. Run: pip install -r requirements.txt"
        ) from exc

    instructions, conversation = _split_messages(messages)
    client = OpenAI(api_key=api_key)
    stream = client.responses.create(
        model=provider_model(DEFAULT_OPENAI_MODEL),
        instructions=instructions or None,
        input=conversation,
        stream=True,
    )

    for event in stream:
        if getattr(event, "type", "") == "response.output_text.delta":
            delta = getattr(event, "delta", "")
            if delta:
                yield delta


def _ollama_stream(
    messages: list[dict[str, str]],
    model: str,
    base_url: str,
    session: Any,
) -> Iterator[str]:
    from core.ollama import ollama_api_url

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "keep_alive": "3m",
    }
    with session.post(
        ollama_api_url(base_url, "chat"),
        json=payload,
        stream=True,
        timeout=(5, 180),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            data: dict[str, Any] = json.loads(line.decode("utf-8"))
            content = data.get("message", {}).get("content", "")
            if content:
                yield content


def stream_chat(
    messages: list[dict[str, str]],
    *,
    ollama_model: str,
    ollama_url: str,
    session: Any,
) -> Iterator[str]:
    """Yield text chunks from the automatically selected chat provider."""
    if provider_name() == "openai":
        yield from _openai_stream(messages)
        return
    yield from _ollama_stream(messages, ollama_model, ollama_url, session)
