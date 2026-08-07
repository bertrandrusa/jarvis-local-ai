# JARVIS Cloud

A cloud-hosted personal assistant powered by Google Gemini, with real-time native voice through the Gemini Live API.

## What runs where

```text
                         permanent GEMINI_API_KEY
                                  │
                                  ▼
Browser ── token request ──► Render / Flask
   │                              │
   │                       short-lived token
   │◄─────────────────────────────┘
   │
   └──── realtime audio/text ───► Gemini Live API
                 ▲                    │
                 └── native audio ────┘
```

Nothing needs to run continuously on your computer. Your phone or computer only needs a modern browser.

## Voice architecture

The primary voice path uses:

- `gemini-3.1-flash-live-preview`
- direct browser-to-Gemini WebSocket audio streaming
- one-session ephemeral tokens minted by Render
- 16 kHz PCM microphone input
- 24 kHz native Gemini audio output
- input and output transcriptions for the on-screen conversation
- server-side voice activity detection so you can speak naturally and interrupt replies

The browser's built-in text-to-speech engine is no longer the main voice system. Voice selection now changes the actual Gemini native voice.

If Live cannot start, typed messages automatically fall back to the regular Gemini text endpoint.

## Voice selection

The interface exposes Gemini's prebuilt voices, including Charon, Gacrux, Orus, Alnilam, Sadaltager, Kore, Puck, Fenrir, Aoede, and others. The selected voice is stored in browser `localStorage` and is applied when the next Live session starts.

## Deploy to Render

1. Create a Gemini API key in Google AI Studio.
2. Create or deploy the Render Blueprint from this repository.
3. In Render, set the secret environment variable:

```text
GEMINI_API_KEY=your_secret_key
```

4. Deploy `main`.
5. Open the Render URL, allow microphone permission, and press the microphone or **Start Live**.

The permanent API key never appears in browser JavaScript. Render only gives the browser a short-lived Live API token.

## Run for development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
python main.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GEMINI_API_KEY="your-key"
python main.py
```

Open `http://localhost:10000`.

## Environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes | None |
| `GEMINI_MODEL` | No | `gemini-3.6-flash` |
| `PORT` | No | `10000` |

## Security

- Never commit the Gemini API key to GitHub.
- Store the permanent key only in Render environment variables.
- Live sessions use short-lived, single-session ephemeral tokens.
- Token responses are intended only for establishing a Gemini Live connection.
- A public deployment can still consume your Gemini quota; add user authentication before sharing the site widely.

## Current scope

The cloud version supports native real-time voice, typed chat, phone/desktop browser access, and conversational interruption. Direct Windows/macOS/Linux desktop control is not part of the cloud runtime because controlling local applications and hardware requires an optional local companion process.
