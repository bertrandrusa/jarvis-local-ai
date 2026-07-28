"""Chat-provider selection and streaming for OpenAI or local Ollama."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OPENAI_MODEL = "gpt-5.6"
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


def provider_name() -> str:
    """Return the configured provider, automatically preferring OpenAI with a key."""
    configured = os.getenv("AI_PROVIDER", "").strip().lower()
    if configured:
        if configured not in {"openai", "ollama"}:
            raise ValueError("AI_PROVIDER must be either 'openai' or 'ollama'.")
        return configured
    return "openai" if os.getenv("OPENAI_API_KEY") else "ollama"


def provider_model(ollama_model: str) -> str:
    if provider_name() == "openai":
        return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
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
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The OpenAI package is not installed. Run: pip install -r requirements.txt"
        ) from exc

    instructions, conversation = _split_messages(messages)
    client = OpenAI()
    stream = client.responses.create(
        model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
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
    session: requests.Session,
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
    session: requests.Session,
) -> Iterator[str]:
    """Yield text chunks from the automatically selected chat provider."""
    if provider_name() == "openai":
        yield from _openai_stream(messages)
        return
    yield from _ollama_stream(messages, ollama_model, ollama_url, session)
