"""JARVIS Cloud: Gemini text fallback plus Gemini Live native audio."""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

from flask import Flask, jsonify, render_template, request
from google import genai

SYSTEM_INSTRUCTION = (
    "You are JARVIS, Bertrand's polished digital assistant and private technical adviser. "
    "VOICE AND DELIVERY: Speak in refined British English with the manner of a sophisticated British butler. "
    "Use a natural modern Received Pronunciation style associated with southern England: precise pronunciation, "
    "crisp consonants, measured pacing, smooth delivery, calm confidence, and restrained emotion. "
    "Aim for a moderately deep, composed, elegant, mature, quietly authoritative presence. "
    "Sound exceptionally competent, discreet, observant, reassuring, and always in control. "
    "Address Bertrand as 'sir' when it feels natural, but do not force it into every sentence. "
    "Use understated British dry wit occasionally. Prefer concise, practical answers and useful next steps. "
    "Avoid American pronunciation and phrasing when a natural British equivalent exists. "
    "Do not sound cartoonishly posh, aristocratic to the point of parody, theatrical, robotic, excessively cheerful, "
    "or overly enthusiastic. Keep the performance subtle and believable rather than exaggerated. "
    "Prioritise privacy, safety, accuracy, and good judgement at all times."
)

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
LIVE_GEMINI_MODEL = "gemini-3.1-flash-live-preview"
RETIRED_MODEL_REPLACEMENTS = {
    "gemini-2.0-flash": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-001": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-lite": DEFAULT_GEMINI_MODEL,
    "gemini-2.0-flash-lite-001": DEFAULT_GEMINI_MODEL,
    "gemini-2.5-flash": DEFAULT_GEMINI_MODEL,
}

app = Flask(__name__)


def _api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured on the server.")
    return api_key


def _client() -> genai.Client:
    return genai.Client(api_key=_api_key())


def _live_client() -> genai.Client:
    # Ephemeral-token provisioning currently uses the v1alpha SDK surface.
    return genai.Client(
        api_key=_api_key(),
        http_options={"api_version": "v1alpha"},
    )


def _model_name() -> str:
    """Return a supported text model, upgrading retired configured values."""
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
    return jsonify(
        {
            "status": "ok",
            "provider": "gemini",
            "text_model": _model_name(),
            "live_model": LIVE_GEMINI_MODEL,
        }
    )


@app.post("/api/live-token")
def live_token():
    """Mint a one-session ephemeral token without exposing the permanent key."""
    live_client: genai.Client | None = None
    try:
        now = dt.datetime.now(tz=dt.timezone.utc)

        # Keep a strong reference to the Gemini client for the entire token
        # request. Calling _live_client().auth_tokens.create(...) inline can
        # let the temporary Client be finalized while its Tokens module is
        # still using the underlying HTTP client.
        live_client = _live_client()
        token = live_client.auth_tokens.create(
            config={
                "uses": 1,
                "expire_time": now + dt.timedelta(minutes=30),
                "new_session_expire_time": now + dt.timedelta(minutes=1),
                "live_connect_constraints": {
                    "model": LIVE_GEMINI_MODEL,
                    "config": {
                        "response_modalities": ["AUDIO"],
                    },
                },
            }
        )
        token_name = token.name

        response = jsonify(
            {
                "token": token_name,
                "model": LIVE_GEMINI_MODEL,
                "expires_in_seconds": 1800,
            }
        )
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception as exc:
        app.logger.exception("Could not create Gemini Live token")
        return jsonify({"error": str(exc)}), 500
    finally:
        if live_client is not None:
            try:
                live_client.close()
            except Exception:
                app.logger.debug("Could not close Gemini Live provisioning client", exc_info=True)


@app.post("/api/chat")
def chat():
    """Text-only fallback used when a Live connection cannot be established."""
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    model = _model_name()
    history = _normalise_history(payload.get("history"))
    contents = [*history, {"role": "user", "parts": [{"text": message}]}]

    try:
        client = _client()
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config={"system_instruction": SYSTEM_INSTRUCTION},
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return jsonify({"reply": text, "model": model, "mode": "text-fallback"})
    except Exception as exc:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
