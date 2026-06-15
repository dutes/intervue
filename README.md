# Intervue

**Intervue** is an AI-powered interview practice tool designed to help you prepare for real-world job interviews. You give it a job spec and your CV, and it runs a multi-round interview panel (Screening, Deep Dive, Challenge), asks pointed questions tailored to your background, and gives you instant, answer-specific feedback.

## ✨ What you get

*   **A tailored panel interview** — questions are anchored to specifics in your CV and the job spec, not generic prompts, and adapt as you answer. The persona shifts each round (supportive → neutral → challenging).
*   **Live progress** — a "Question X of Y" meter as you go.
*   **Per-answer coaching** — strengths, what to improve, and an improved STAR rewrite of your own answer.
*   **A detailed report** — overall score, strengths/opportunities, competency breakdown, how you handled each interviewer style, a 7-day practice plan, and the full transcript. Export it to PDF with the **Save Report** button.

## 🤖 Bring your own model

Intervue doesn't ship with a model — you choose a provider and paste your own API key on the New Session screen. Supported options:

| Provider | Notes |
| --- | --- |
| **OpenAI (GPT)** | API key from [platform.openai.com](https://platform.openai.com/) |
| **Anthropic (Claude)** | API key from [console.anthropic.com](https://console.anthropic.com/) |
| **Google (Gemini)** | API key from [aistudio.google.com](https://aistudio.google.com/) |
| **Local / Custom** | Any OpenAI-compatible server (Ollama, LM Studio, vLLM, etc.) — supply a base URL, no API key needed. Runs fully offline. |
| **Mock** | No key, no network — canned responses for trying out the UI. |

**Choosing a model:** after entering your key (or base URL for local), click **Load models** to fetch the models your account/server offers, or pick **Custom…** to type any model ID. Leave it on the default to skip. A faster model (e.g. `gemini-2.0-flash`, `claude-sonnet-4-6`) gives a quicker start, since each interview begins with a few setup calls.

## 🚀 Quick Start Guide

The easiest way to run Intervue is using **Docker**. This bundles everything into a single package so you don't need to install Python or Node.js manually.

### 1. Prerequisites

*   **Download & Install Docker Desktop**: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
    *   *Note: Ensure Docker Desktop is running before proceeding.*
*   **An API key** for your chosen provider (OpenAI, Anthropic, or Google) — just have it ready to paste. Not needed if you use a Local model or Mock mode.

### 2. Get the Code

1.  **Download**: Click the green **Code** button at the top right of this GitHub page and select **Download ZIP**.
2.  **Unzip**: Extract the folder to somewhere easy to find (e.g., your Desktop).

### 3. Run the App

1.  Open your computer's terminal:
    *   **Windows**: Press `Win + R`, type `cmd`, and press Enter.
    *   **Mac**: Press `Cmd + Space`, type `Terminal`, and press Enter.
2.  Navigate to the folder you unzipped (the ZIP extracts to `intervue-main`). For example:
    ```bash
    cd Desktop/intervue-main
    ```
3.  Run this command to start the app:
    ```bash
    docker compose up --build
    ```
    *   *This process might take a few minutes the first time as it downloads necessary tools.*
    *   *If you rebuild after updating the code, use `docker compose build --no-cache` to avoid stale layers.*

### 4. Start Practicing!

Once the terminal shows logs saying the server is running, open your web browser and go to:

👉 **[http://localhost:8000](http://localhost:8000)**

### 🛑 Stopping the App

To stop the application, just go back to your terminal window and press `Ctrl + C`.

---

## 🔧 Advanced / Developer Setup

If you prefer to run the code manually without Docker (for development or customization), follow these steps.

### Backend Setup (Python)

```bash
# Create a virtual environment
python -m venv .venv
# Activate it (Windows: .venv\Scripts\activate, Mac/Linux: source .venv/bin/activate)

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn server.main:app --reload
```

### Frontend Setup (React)

```bash
cd client_web
npm install
npm run dev
```

The dev server proxies API calls to the backend on port 8000, so run both together.

### Optional environment variables

*   `LLM_REQUEST_TIMEOUT` — seconds to wait for a model response (default `120`).
*   `OPENAI_MODEL` / `ANTHROPIC_MODEL` / `GEMINI_MODEL` — default model when none is chosen in the UI.

## Data Privacy

All your interview sessions and reports are saved locally on your computer in the `data/` folder inside the project directory. Your answers are sent only to the AI provider you select, for processing. If you choose a **Local** model or **Mock** mode, nothing leaves your machine at all. Your API key is held in memory only for the duration of a session and is never written to disk.
