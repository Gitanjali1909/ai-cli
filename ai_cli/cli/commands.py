import json
from pathlib import Path
import subprocess
from typing import Literal, List
from concurrent.futures import ThreadPoolExecutor

import typer
from rich.console import Console
from rich.text import Text

from ai_cli.core.llm import generate_response
from ai_cli.core.prompts import explain_prompt, fix_prompt, review_prompt
from ai_cli.core.chunking import chunk_text
from ai_cli.core.aggregator import aggregate_responses

console = Console()
PROJECT_ROOT = Path.cwd()
LAST_FILE = PROJECT_ROOT / ".ai_cli_last.json"
SKIPPED_DIRS = {".git", ".venv", "__pycache__", "ai_cli.egg-info", "node_modules"}
TEXT_SUFFIXES = {".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".json", ".toml", ".yaml", ".yml"}
MAX_MODEL_LINES = 200
MAX_MODEL_CHARS = 8000
CHUNK_SIZE = 4000
CHUNK_OVERLAP = 400
ModelName = Literal["phi", "gemma"]

EXPLAIN_HEADINGS = ("Overview", "Key Components", "Execution Flow", "Simple Explanation", "Combined Summary Report")
FIX_HEADINGS = ("Overview", "Issues", "Suggestions", "Improved Code")
REVIEW_HEADINGS = ("Overview", "Issues", "Suggestions", "Improved Code")


def read_file(path: str) -> str:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(path)

    # Adding errors="replace" prevents UnicodeDecodeError on files with non-UTF-8 characters
    content = file_path.read_text(encoding="utf-8", errors="replace")
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


def remove_empty_and_comment_lines(content: str) -> str:
    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("//"):
            continue
        lines.append(line)
    return "\n".join(lines)


def call_ai_multi_chunk(
    chunks: List[str],
    prompt_fn,
    command: str,
    headings,
    model: str,
    stream: bool,
    verbose: bool,
    task_type: str,
) -> str | None:
    if verbose:
        console.print(f"Model: {model}", style="dim")
        console.print(f"Streaming: {stream}", style="dim")

    if stream and verbose:
        console.print("Streaming is disabled by the current Ollama request config.", style="yellow")

    responses = [None] * len(chunks)

    def process_chunk(index: int, chunk: str):
        if len(chunks) > 1:
            chunk_context = f"This is part {index} of {len(chunks)} of a larger context. Focus only on this section.\n\n{chunk}"
        else:
            chunk_context = chunk
            
        prompt = prompt_fn(chunk_context)
        output = generate_response(prompt, model=model)
        return index, output

    with console.status("[cyan]Waiting for AI processing chunks in parallel...[/cyan]", spinner="dots"):
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_chunk, idx, chunk) for idx, chunk in enumerate(chunks, start=1)]
            for future in futures:
                idx, output = future.result()
                if output.startswith("Error:"):
                    console.print(f"\nError processing chunk {idx}: {output}", style="bold red")
                    responses[idx - 1] = f"Error in this part: {output}"
                else:
                    responses[idx - 1] = output

    # Check if all chunks failed
    if all(res.startswith("Error in this part:") for res in responses):
        return None

    final_output = aggregate_responses(responses, task_type=task_type)
    render_output(final_output, headings)
    save_last(command, final_output)
    return final_output


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

    cleaned_source = remove_empty_and_comment_lines(source)
    chunks = chunk_text(cleaned_source, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    prompt_fn = fix_prompt if result.returncode else explain_prompt
    task_type = "general" if result.returncode else "summary"
    headings = FIX_HEADINGS if result.returncode else EXPLAIN_HEADINGS
    
    return call_ai_multi_chunk(chunks, prompt_fn, f"run {cmd}", headings, model, stream, verbose, task_type)


def explain(
    file_path: str,
    model: ModelName = typer.Option("phi", "--model", help="Ollama model to use."),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Stream output from Ollama."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra command details."),
    full: bool = typer.Option(True, "--full/--no-full", help="Process every chunk one by one."),
) -> None:
    content = read_input(file_path)
    if content is None:
        return

    cleaned_content = remove_empty_and_comment_lines(content)
    chunks = chunk_text(cleaned_content, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    selected_chunks = chunks if full else chunks[:1]
    
    call_ai_multi_chunk(selected_chunks, explain_prompt, f"explain {file_path}", EXPLAIN_HEADINGS, model, stream, verbose, "summary")


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

    cleaned_content = remove_empty_and_comment_lines(content)
    chunks = chunk_text(cleaned_content, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    
    call_ai_multi_chunk(chunks, fix_prompt, "fix", FIX_HEADINGS, model, stream, verbose, "general")


def review(
    file_path: str,
    model: ModelName = typer.Option("phi", "--model", help="Ollama model to use."),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Stream output from Ollama."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show extra command details."),
    full: bool = typer.Option(True, "--full/--no-full", help="Process every chunk one by one."),
) -> None:
    content = read_input(file_path)
    if content is None:
        return

    cleaned_content = remove_empty_and_comment_lines(content)
    chunks = chunk_text(cleaned_content, max_chars=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    selected_chunks = chunks if full else chunks[:1]
    
    call_ai_multi_chunk(selected_chunks, review_prompt, f"review {file_path}", REVIEW_HEADINGS, model, stream, verbose, "general")


def last() -> None:
    if not LAST_FILE.is_file():
        console.print("No previous AI response found.", style="yellow")
        return

    data = json.loads(LAST_FILE.read_text(encoding="utf-8"))
    console.print(Text(data.get("command", "last"), style="bold cyan"))
    console.print(data.get("response", ""))