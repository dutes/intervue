# Intervue

**Intervue** is an AI-powered interview practice tool designed to help you prepare for real-world job interviews. It simulates different interview stages (Screening, Deep Dive, Challenge) and provides instant feedback on your answers.

## 🚀 Quick Start Guide (For Everyone)

The easiest way to run Intervue is using **Docker**. This bundles everything into a single package so you don't need to install Python or Node.js manually.

### 1. Prerequisites

*   **Download & Install Docker Desktop**: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
    *   *Note: Ensure Docker Desktop is running before proceeding.*
*   **Get an AI API Key**: You will need an API key from either [OpenAI](https://platform.openai.com/) (for ChatGPT) or [Google](https://aistudio.google.com/) (for Gemini).
    *   *You don't need to install anything for this, just have the key ready to paste when you start the interview.*

### 2. Get the Code

1.  **Download**: Click the green **Code** button at the top right of this GitHub page and select **Download ZIP**.
2.  **Unzip**: Extract the folder to somewhere easy to find (e.g., your Desktop).

### 3. Run the App

1.  Open your computer's terminal:
    *   **Windows**: Press `Win + R`, type `cmd`, and press Enter.
    *   **Mac**: Press `Cmd + Space`, type `Terminal`, and press Enter.
2.  Navigate to the folder you unzipped. For example:
    ```bash
    cd Desktop/interview_game-main
    ```
3.  Run this command to start the app:
    ```bash
    docker compose up --build
    ```
    *   *This process might take a few minutes the first time as it downloads necessary tools.*

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

## Data Privacy

All your interview sessions and reports are saved locally on your computer in the `data/` folder inside the project directory. Nothing is sent to the cloud except strictly for processing your answers via the AI provider (OpenAI or Google) you select.
