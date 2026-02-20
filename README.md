# Intervue

**Intervue** is a privacy-first, AI-powered interview practice tool designed specifically for job seekers. It provides a realistic, self-contained environment to sharpen your technique, test your knowledge, and receive honest feedback—all without your data ever leaving your machine (except for processing by your chosen AI provider).

## ✨ Core Features (Current)

*   **Role-Aware Simulation**: Tailors every question to the specific Job Description and CV you provide.
*   **Three-Stage Interview**: Progresses through Screening, Deep Dive, and Challenge rounds to test different levels of depth.
*   **Voice & Text Input**: Practice exactly how you'll perform. Use voice input with real-time transcription or type your responses.
*   **Numerical Scoring**: Get a concrete 0-10 score for every session based on a weighted competency rubric.
*   **Actionable Feedback**: Receives a structured report highlighting your specific "Strengths" and "Areas to Improve."
*   **Session History**: Review all your past transcripts, scores, and feedback reports in a dedicated local dashboard.
*   **100% Data Ownership**: Your transcripts, session logs, and reports are saved locally.
=======
**Intervue** is an AI-powered interview practice tool designed to help you prepare for real-world job interviews. It simulates different interview stages (Screening, Deep Dive, Challenge) and provides instant feedback on your answers.

## 🚀 Quick Start Guide 
The easiest way to run Intervue is using **Docker**. This bundles everything into a single package so you don't need to install Python or Node.js manually.
>>>>>>> a77647888a1b8511f585298219bd7beafd9aa1da

## 🔒 Data Privacy & Protection

Intervue is built with a "Local-First" philosophy. We take your data privacy seriously:

*   **Zero Telemetry**: We do not track your usage, collect analytics, or "ping home."
*   **No Intervue Server Storage**: We never send your session data to any server we control. Your transcripts and notes stay in the `data/` folder on your machine.
*   **No API Key Persistence**: Your AI API keys are handled via environment variables/memory and are **never** saved to disk in your session files.
*   **Direct-to-Provider Processing**: Your data is only sent to the AI provider you explicitly select (OpenAI or Google) for the purpose of generating questions and feedback.


> [!NOTE]
> Your data is only sent to the AI provider you explicitly select (OpenAI or Google) for the purpose of generating questions and feedback.

---

## 🚀 Quick Start Guide

The easiest way to run Intervue is using **Docker**. This bundles everything (Backend, Frontend, and Storage) into a single, isolated package.

### 1. Prerequisites

*   **Docker Desktop**: [Download & Install here](https://www.docker.com/products/docker-desktop/). Make sure it's running.
*   **AI API Key**: You'll need an API key from [OpenAI](https://platform.openai.com/) (ChatGPT) or [Google](https://aistudio.google.com/) (Gemini).

### 2. Setup

1.  **Download this repository** as a ZIP file and extract it.
2.  Open your **Terminal** or **Command Prompt**.
3.  Navigate to the folder:
    ```bash
    cd path/to/interview_game
    ```
4.  Launch the app:
    ```bash
    docker compose up --build
    ```

### 3. Start Practicing

Once the logs show the server is ready, open your browser to:

👉 **[http://localhost:8000](http://localhost:8000)**

---

## 🔧 Developer Setup (Manual)

If you'd like to run the components separately for development:

### Backend (Python)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server.main:app --reload
```

### Frontend (React)
```bash
cd client_web
npm install
npm run dev
```
