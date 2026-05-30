import json
from pathlib import Path
import subprocess
from typing import Literal

import typer
from rich.console import Console
from rich.text import Text

from ai_cli.core.llm import generate_response
from ai_cli.core.prompts import explain_prompt, fix_prompt, review_prompt

console = Console()
PROJECT_ROOT = Path.cwd()
LAST_FILE = PROJECT_ROOT / ".ai_cli_last.json"
SKIPPED_DIRS = {".git", ".venv", "__pycache__", "ai_cli.egg-info", "node_modules"}
TEXT_SUFFIXES = {".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"}
MAX_MODEL_LINES = 200
MAX_MODEL_CHARS = 8000
ModelName = Literal["phi", "gemma"]

EXPLAIN_HEADINGS = ("Overview", "Key Components", "Execution Flow", "Simple Explanation")
FIX_HEADINGS = ("Overview", "Issues", "Suggestions", "Improved Code")
REVIEW_HEADINGS = ("Overview", "Issues", "Suggestions", "Improved Code")


def read_file(path: str) -> str:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(path)

    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError("empty file")

    return content


def read_input(path: str) -> str | None:
    input_path = Path(path).expanduser()
    if input_path.is_file():
        return read_single_file(input_path)
    if input_path.is_dir():
        return read_folder(input_path)

    console.print("File not found. Check path.", style="bold red")
    return None


def read_single_file(path: Path) -> str | None:
    try:
        return f"File: {path}\n\n{read_file(str(path))}"
    except FileNotFoundError:
        console.print("File not found. Check path.", style="bold red")
    except ValueError:
        console.print("File is empty.", style="bold red")
    except (OSError, UnicodeDecodeError):
        console.print("Could not read this file safely.", style="bold red")
    return None


def read_folder(path: Path) -> str | None:
    parts = []
    for file_path in sorted(path.rglob("*")):
        if any(part in SKIPPED_DIRS for part in file_path.parts):
            continue
        if not file_path.is_file() or file_path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = read_file(str(file_path))
        except (FileNotFoundError, ValueError, OSError, UnicodeDecodeError):
            continue
        parts.append(f"File: {file_path.relative_to(path)}\n\n{content}")

    if not parts:
        console.print("No readable files found in folder.", style="bold red")
        return None

    return "\n\n---\n\n".join(parts)


def trim_code(code: str, max_chars: int = MAX_MODEL_CHARS):
    return code[:max_chars]


def limit_model_input(
    content: str,
    max_lines: int = MAX_MODEL_LINES,
    max_chars: int = MAX_MODEL_CHARS,
) -> str:
    lines = content.splitlines()
    line_limited = "\n".join(lines[:max_lines])
    limited = trim_code(line_limited, max_chars)

    if limited == content:
        return content

    return f"{limited}\n\n[Input truncated to first {max_lines} lines or {max_chars} characters.]"


def call_ai(
    prompt: str,
    command: str,
    headings,
    model: str,
    stream: bool,
    verbose: bool,
) -> str | None:
    if verbose:
        console.print(f"Model: {model}", style="dim")
        console.print(f"Streaming: {stream}", style="dim")

    if stream and verbose:
        console.print("Streaming is disabled by the current Ollama request config.", style="yellow")

    with console.status("[cyan]Waiting for AI...[/cyan]", spinner="dots"):
        output = generate_response(prompt, model=model)

    if output.startswith("Error:"):
        console.print(output, style="bold red")
    else:
        render_output(output, headings)

    if output.startswith("Error:"):
        return None

    save_last(command, output)
    return output


def render_output(output: str, headings) -> None:
    current_heading = None

    for raw_line in output.strip().splitlines():
        line = raw_line.strip()
        if not line:
            console.print()
            continue

        heading = normalize_heading(line, headings)
        if heading:
            if current_heading:
                console.print()
            current_heading = heading
            console.print(Text(heading, style="bold cyan"))
            continue

        console.print(Text(line, style=line_style(current_heading)))


def normalize_heading(line: str, headings):
    cleaned = line.strip("*# ").rstrip(":").strip()
    return cleaned if cleaned in headings else None


def line_style(current_heading: str | None) -> str:
    if current_heading == "Issues":
        return "red"
    if current_heading in {"Suggestions", "Improved Code"}:
        return "green"
    return "white"


def save_last(command: str, response: str) -> None:
    LAST_FILE.write_text(
        json.dumps({"command": command, "response": response}, indent=2),
        encoding="utf-8",
    )


def run_command(
    cmd: str,
    model: ModelName = "phi",
    stream: bool = False,
    verbose: bool = False,
) -> str | None:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    source = result.stderr.strip() if result.returncode else result.stdout.strip()
    if not source:
        source = "Command produced no output."

    source = limit_model_input(source)
    prompt = fix_prompt(source) if result.returncode else explain_prompt(source)
    return call_ai(prompt, f"run {cmd}", FIX_HEADINGS, model, stream, verbose)


def explain(
    file_path: str,
    model: ModelName = typer.Option("phi", "--model", help="Ollama model to use."),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Stream output from Ollama."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra command details."),
) -> None:
    content = read_input(file_path)
    if content is None:
        return

    content = limit_model_input(content)
    call_ai(explain_prompt(content), f"explain {file_path}", EXPLAIN_HEADINGS, model, stream, verbose)


def fix(
    input: str,
    model: ModelName = typer.Option("phi", "--model", help="Ollama model to use."),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Stream output from Ollama."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra command details."),
) -> None:
    input_path = Path(input).expanduser()
    content = read_input(input) if input_path.exists() else input
    if content is None:
        return

    content = limit_model_input(content)
    call_ai(fix_prompt(content), "fix", FIX_HEADINGS, model, stream, verbose)


def review(
    file_path: str,
    model: ModelName = typer.Option("phi", "--model", help="Ollama model to use."),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Stream output from Ollama."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra command details."),
) -> None:
    content = read_input(file_path)
    if content is None:
        return

    content = limit_model_input(content)
    call_ai(review_prompt(content), f"review {file_path}", REVIEW_HEADINGS, model, stream, verbose)


def last() -> None:
    if not LAST_FILE.is_file():
        console.print("No previous AI response found.", style="yellow")
        return

    data = json.loads(LAST_FILE.read_text(encoding="utf-8"))
    console.print(Text(data.get("command", "last"), style="bold cyan"))
    console.print(data.get("response", ""))
