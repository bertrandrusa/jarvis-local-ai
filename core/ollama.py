"""Small helpers for building consistent Ollama API requests."""

from collections.abc import Iterable

DEFAULT_OLLAMA_URL = "http://localhost:11434"


def normalize_ollama_url(url: str | None) -> str:
    """Return an Ollama server URL without a trailing ``/api`` segment."""
    normalized = (url or DEFAULT_OLLAMA_URL).strip().rstrip("/")
    normalized = normalized.removesuffix("/api")
    return normalized.rstrip("/")


def ollama_api_url(url: str | None, endpoint: str) -> str:
    """Build an Ollama API URL from either a host URL or an ``/api`` URL."""
    clean_endpoint = endpoint.strip("/")
    clean_endpoint = clean_endpoint.removeprefix("api/")
    return f"{normalize_ollama_url(url)}/api/{clean_endpoint}"


def trim_messages(messages: Iterable[dict], limit: int) -> list[dict]:
    """Keep the system message and the most recent conversation messages."""
    items = list(messages)
    if limit < 1 or len(items) <= limit:
        return items

    if items and items[0].get("role") == "system":
        return [items[0], *items[-(limit - 1) :]]
    return items[-limit:]
