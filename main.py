"""JARVIS Cloud: a lightweight Gemini-powered web assistant."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template, request
from google import genai

SYSTEM_INSTRUCTION = (
    "You are JARVIS, Bertrand's polished digital assistant. "
    "Use calm British formality, be concise and practical, and address Bertrand "
    "as 'sir' when natural. Use occasional dry wit without becoming rude. "
    "Prioritise privacy, safety, accuracy, and useful next steps."
)

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
RETIRED_MODEL_REPLACEMENTS = {
    "gemini-2.0-flash": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-001": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-lite": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-lite-001": DEFAULT_GEMINI_MODEL,
    "gemini-2.5-flash": DEFAULT_GEMINI_MODEL,
}

app = Flask(__name__)


def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured on the server.")
    return genai.Client(api_key=api_key)


def _model_name() -> str:
    """Return a supported Gemini model, upgrading retired configured values."""
    configured = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
    if not configured:
        return DEFAULT_GEMINI_MODEL
    return RETIRED_MODEL_REPLACEMENTS.get(configured, configured)


def _normalise_history(raw_history: Any) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    if not isinstance(raw_history, list):
        return history

    for item in raw_history[-20:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        text = str(item.get("text", "")).strip()
        if role not in {"user", "model"} or not text:
            continue
        history.append({"role": role, "parts": [{"text": text}]})
    return history


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "provider": "gemini", "model": _model_name()})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    model = _model_name()
    history = _normalise_history(payload.get("history"))
    contents = [*history, {"role": "user", "parts": [{"text": message}]}]

    try:
        # Keep the client alive for the entire request. Creating a chat from a
        # temporary client can allow the underlying HTTP client to be closed
        # before the request is sent.
        client = _client()
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={"system_instruction": SYSTEM_INSTRUCTION},
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return jsonify({"reply": text, "model": model})
    except Exception as exc:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
