from difflib import get_close_matches
from pathlib import Path
import re
from textwrap import fill

from rich.console import Console
from rich.text import Text

from ai_cli.core.llm import ask_llm

console = Console()
PROJECT_ROOT = Path.cwd()
SKIPPED_DIRS = {".git", ".venv", "__pycache__", "ai_cli.egg-info"}

RESPONSE_RULES = """
Return a concise, structured developer-tool answer.
Use short lines and bullet points where helpful.
Avoid huge paragraphs and unnecessary explanation.
Focus on clarity over length.
"""

EXPLAIN_CODE_RULES = """
Explain the code like a senior developer teaching a junior developer.
Be concise but clear, and avoid generic statements.
Only use information present in the given code.
Never mention libraries, functions, or behavior not present in the code.
Do not assume libraries or functionality not shown.
If something is unclear, say "Not स्पष्ट from code".
Do not invent examples unrelated to the code.
Directly reference actual code elements from the provided code.
When explaining, reference actual code snippets in backticks.
Example style: "The line `app = typer.Typer()` initializes the CLI app."
Use this exact structure:
1. Overview
2. Key Components
3. Step-by-step flow
4. Example
5. Simple explanation

For each section:
- Overview: say what this specific code does.
- Key Components: explain important imports, functions, classes, or variables.
- Step-by-step flow: describe the execution path.
- Example: include a tiny example only if it helps.
- Simple explanation: explain it in ELI5 style.

Use bullets where helpful.
Keep each point specific to the code provided.
"""

SECTION_HEADINGS = {
    "Overview",
    "Key Components",
    "Step-by-step flow",
    "Example",
    "Simple explanation",
    "Explanation",
    "How it works",
}


def render_ai_output(output: str) -> None:
    printed = False
    has_heading = any(
        parse_heading(line.strip()) in SECTION_HEADINGS
        for line in output.strip().splitlines()
    )

    if not has_heading:
        console.print(Text("Overview", style="bold cyan"))
        printed = True

    for raw_line in output.strip().splitlines():
        line = raw_line.strip()
        if not line:
            if printed:
                console.print()
            continue

        heading = parse_heading(line)
        if heading in SECTION_HEADINGS:
            if printed:
                console.print()
            console.print(Text(heading, style="bold cyan"))
            printed = True
            continue

        console.print(Text(format_body_line(line), style="green"))
        printed = True


def parse_heading(line: str):
    cleaned = re.sub(r"^\s*\d+[\).]\s*", "", line).strip()
    cleaned = cleaned.strip("*_# ").rstrip(":").strip()
    return cleaned if cleaned in SECTION_HEADINGS else None


def format_body_line(line: str) -> str:
    bullet_match = re.match(r"^([-*•]\s+)(.*)", line)
    if bullet_match:
        bullet, body = bullet_match.groups()
        return fill(
            body,
            width=86,
            initial_indent=f"{bullet}",
            subsequent_indent="  ",
        )

    return fill(line, width=88)


def iter_project_files():
    for path in PROJECT_ROOT.rglob("*"):
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def find_project_file(file_path: str):
    try:
        requested_path = Path(file_path).expanduser()
        requested_parts = requested_path.parts
        requested_name = requested_path.name
        if requested_path.is_file():
            return requested_path, None
    except (OSError, RuntimeError, ValueError):
        requested_parts = Path(file_path).parts
        requested_name = Path(file_path).name

    files = list(iter_project_files())
    exact_matches = [
        path
        for path in files
        if path.name == requested_name
        or path.parts[-len(requested_parts) :] == requested_parts
    ]

    if exact_matches:
        return exact_matches[0], None

    relative_paths = [str(path.relative_to(PROJECT_ROOT)) for path in files]
    candidates = relative_paths + [path.name for path in files]
    matches = get_close_matches(file_path, candidates, n=1, cutoff=0.45)

    if not matches:
        return None, None

    match = matches[0]
    for path in files:
        if match in {str(path.relative_to(PROJECT_ROOT)), path.name}:
            return None, path

    return None, None


def show_file_not_found(suggestion=None) -> None:
    console.print(
        "File not found. Try giving full path like ai_cli/main.py",
        style="bold red",
    )
    if suggestion:
        console.print(
            f"Closest match: {suggestion.relative_to(PROJECT_ROOT)}",
            style="yellow",
        )


def explain_code(file_path: str):
    path, suggestion = find_project_file(file_path)
    if path is None:
        show_file_not_found(suggestion)
        return

    try:
        code = path.read_text()
    except (OSError, UnicodeDecodeError):
        console.print("Could not read this file safely.", style="bold red")
        return

    prompt = f"{RESPONSE_RULES}\n{EXPLAIN_CODE_RULES}\nCode:\n\n{code}"
    render_ai_output(ask_llm(prompt))


def fix_bug(file_path: str):
    with open(file_path, "r") as f:
        error = f.read()

    prompt = f"{RESPONSE_RULES}\nFix this error:\n\n{error}"
    render_ai_output(ask_llm(prompt))
