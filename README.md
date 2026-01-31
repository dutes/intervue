# Interview Game (Local Only)

A terminal-based interview practice game with a local FastAPI server and a Typer/Rich terminal client. All data is stored locally in JSON, and LLM access (OpenAI or Gemini) is done **only** via `curl` subprocess calls from the server.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Choose one provider and set the API key (or enter it when the CLI prompts you):

```bash
export OPENAI_API_KEY=your_key
# optional: export OPENAI_MODEL=gpt-4.1-mini

# or
export GEMINI_API_KEY=your_key
# optional: export GEMINI_MODEL=gemini-1.5-flash
```

## Run the Server

```bash
uvicorn server.main:app --reload
```

## Run the Client

```bash
python client/cli.py
```

## Web UI

Open `http://127.0.0.1:8000` to use the web client. You'll be prompted for your provider and API key in a setup dialog before starting a session.

## Mock Mode

If you want to run without any LLM access, pick the `mock` provider when prompted. It generates deterministic placeholder questions and scores.

## Data Output

All sessions and reports are written to `data/`:

- `data/sessions/<session_id>.json`
- `data/reports/<session_id>/report.json`
- `data/reports/<session_id>/*.png`
