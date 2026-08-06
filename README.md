# JARVIS Cloud

A browser-based AI assistant powered by the Google Gemini API and designed for cloud hosting on Render.

## What changed

This branch replaces the Windows PySide6/Ollama desktop entry point with:

- a Flask web application
- a responsive browser chat interface
- Google Gemini as the AI provider
- Render deployment configuration
- server-side API-key storage

Nothing needs to run on your computer after deployment. Your device only opens the website.

## Architecture

```text
Browser → Render Flask app → Gemini API
```

The browser never receives the Gemini API key. Render stores it as a secret environment variable.

## Deploy to Render

1. Create a Gemini API key in Google AI Studio.
2. Sign in to Render and create a **Blueprint** from this GitHub repository.
3. Select the `gemini-cloud-web` branch while reviewing this pull request, or deploy `main` after merging it.
4. When Render requests environment variables, enter:

```text
GEMINI_API_KEY=your_secret_key
```

The included `render.yaml` configures the remaining settings automatically.

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
| `GEMINI_MODEL` | No | `gemini-2.5-flash` |
| `PORT` | No | `10000` |

## Security

- Never commit an API key to GitHub.
- Store the key only in Render's environment-variable settings.
- The key remains on the server and is not included in browser JavaScript.

## Current scope

The cloud version supports Gemini chat and browser access from phones and computers. Windows desktop automation, local smart-home discovery, local wake-word listening, and other hardware-dependent functions are not included because those require software running on the local machine.
