from __future__ import annotations

import sys
from typing import List

import requests
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

API_URL = "http://127.0.0.1:8000"
app = typer.Typer()
console = Console()


def read_multiline(prompt: str) -> str:
    console.print(Panel(prompt, title="Input", box=box.ROUNDED))
    console.print("Enter text. Finish with a single line containing END.")
    lines: List[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def choose_provider() -> str:
    provider = typer.prompt("Choose provider: openai / gemini / mock", default="openai")
    return provider.strip().lower()


def prompt_api_key(provider: str) -> str | None:
    if provider not in {"openai", "gemini"}:
        return None
    key = typer.prompt(
        f"Enter {provider} API key (leave blank to use server env)",
        default="",
        show_default=False,
        hide_input=True,
    )
    return key.strip() or None


def start_session(provider: str, job_spec: str, cv_text: str, api_key: str | None) -> str:
    response = requests.post(
        f"{API_URL}/sessions/start",
        json={
            "job_spec": job_spec,
            "cv_text": cv_text,
            "provider": provider,
            "api_key": api_key,
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(response.json().get("detail", "Failed to start session"))
    return response.json()["session_id"]


@app.command()
def main() -> None:
    console.print(Panel("Interview Game", style="bold cyan"))

    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code != 200:
            console.print("Server health check failed.")
            raise typer.Exit(code=1)
    except requests.RequestException as exc:
        console.print(f"Unable to reach server: {exc}")
        raise typer.Exit(code=1) from exc

    provider = choose_provider()
    api_key = prompt_api_key(provider)
    job_spec = read_multiline("Paste the job specification.")
    cv_text = read_multiline("Paste your CV/resume text.")

    while True:
        try:
            session_id = start_session(provider, job_spec, cv_text, api_key)
            break
        except RuntimeError as exc:
            console.print(f"[red]LLM connectivity failed:[/red] {exc}")
            if "API_KEY is not set" in str(exc) and provider in {"openai", "gemini"}:
                console.print("[yellow]API key missing. Please enter it to continue.[/yellow]")
                api_key = prompt_api_key(provider)
                if api_key:
                    continue
            action = typer.prompt("Retry / switch / mock / exit", default="retry").strip().lower()
            if action == "retry":
                continue
            if action == "switch":
                provider = choose_provider()
                api_key = prompt_api_key(provider)
                continue
            if action == "mock":
                provider = "mock"
                api_key = None
                continue
            raise typer.Exit(code=1)

    console.print(f"Session started: {session_id}")

    total_questions = 5
    for _ in range(total_questions):
        q_resp = requests.post(f"{API_URL}/sessions/{session_id}/next_question", timeout=60)
        if q_resp.status_code != 200:
            console.print("Interview complete or failed to fetch question.")
            break
        question = q_resp.json()
        console.print(Panel(question["text"], title=f"{question['round']} ({question['persona']})"))
        answer = read_multiline("Your answer:")
        a_resp = requests.post(
            f"{API_URL}/sessions/{session_id}/answer",
            json={"question_id": question["question_id"], "answer_text": answer},
            timeout=60,
        )
        if a_resp.status_code != 200:
            console.print("Failed to submit answer.")
            break

    end_resp = requests.post(f"{API_URL}/sessions/{session_id}/end", timeout=60)
    if end_resp.status_code != 200:
        console.print("Failed to close session.")
        raise typer.Exit(code=1)

    payload = end_resp.json()
    summary = payload["summary"]
    report_paths = payload["report_paths"]

    console.print(Panel(f"Overall Score: {summary['overall_score']}", title="Results"))

    table = Table(title="Strengths / Weaknesses", box=box.SIMPLE)
    table.add_column("Strengths")
    table.add_column("Weaknesses")
    max_len = max(len(summary["strengths"]), len(summary["weaknesses"]))
    for i in range(max_len):
        strength = summary["strengths"][i] if i < len(summary["strengths"]) else ""
        weakness = summary["weaknesses"][i] if i < len(summary["weaknesses"]) else ""
        table.add_row(strength, weakness)
    console.print(table)

    for feedback in summary["persona_feedback"]:
        panel_lines = [
            "[bold]Positives[/bold]",
            *[f"- {item}" for item in feedback["positives"]],
            "",
            "[bold]Concerns[/bold]",
            *[f"- {item}" for item in feedback["concerns"]],
            "",
            f"[bold]Next:[/bold] {feedback['next_step']}",
        ]
        console.print(Panel("\n".join(panel_lines), title=f"{feedback['persona'].title()} Interviewer"))

    console.print("Report assets saved:")
    for name, path in report_paths.items():
        console.print(f"- {name}: {path}")


if __name__ == "__main__":
    app()
