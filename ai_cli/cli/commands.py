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

EXPLAIN_SECTION_HEADINGS = {
    "Overview",
    "Key Components",
    "Execution Flow",
    "Simple Explanation",
}

REVIEW_SECTION_HEADINGS = {
    "Code Quality Issues",
    "Bugs / Risks",
    "Suggestions",
    "Improved Code Snippets",
}

SECTION_HEADINGS = EXPLAIN_SECTION_HEADINGS | REVIEW_SECTION_HEADINGS | {
    "Key Parts",
    "Execution flow",
    "Important note",
    "Step-by-step flow",
    "Example",
    "Simple explanation",
    "Explanation",
    "How it works",
}

EXPLAIN_CODE_RULES = """
STRICT FORMAT.
Output ONLY these sections, in this exact order:
1. Overview
2. Key Components
3. Execution Flow
4. Simple Explanation

Rules:
- Keep the full output under 150 words.
- Be direct and technical.
- Only use information present in the given code.
- Never mention libraries, functions, or behavior not present in the code.
- Do not assume libraries or functionality not shown.
- If something is unclear, say "Not स्पष्ट from code".
- Reference actual code snippets in backticks when useful.
- Do not include anything unrelated to the given code.
- Do not add extra sections.
- Do not create stories, puzzles, scenarios, rules, games, or examples.
- Do not invent rules or examples.
- Never create hypothetical scenarios.
- Never simulate multiple users.
- Never use "imagine", "suppose", or "let's say".
"""

REVIEW_RULES = """
Review the code like a senior developer reviewing a PR.
Only use information present in the given code.
Never mention libraries, functions, or behavior not present in the code.
Be concise, direct, and constructive.
Prioritize real risks over style nitpicks.
Reference actual code snippets in backticks when explaining issues.
Do not repeat the entire code block.
Do not repeat sections.
Use this exact structure:
1. Code Quality Issues
2. Bugs / Risks
3. Suggestions
4. Improved Code Snippets

For each section:
- Code Quality Issues: point out maintainability, naming, structure, or readability concerns.
- Bugs / Risks: call out behavior that may fail or produce incorrect results.
- Suggestions: give practical fixes a developer can apply.
- Improved Code Snippets: include only small, relevant snippets when useful.
"""


def render_ai_output(
    output: str,
    allowed_headings=None,
    default_heading: str = "Overview",
) -> None:
    allowed_headings = allowed_headings or SECTION_HEADINGS
    output = clean_ai_output(output, allowed_headings)
    printed = False
    has_heading = any(
        parse_heading(line.strip(), allowed_headings) in allowed_headings
        for line in output.strip().splitlines()
    )

    if not has_heading:
        console.print(Text(default_heading, style="bold cyan"))
        printed = True

    for raw_line in output.strip().splitlines():
        line = raw_line.strip()
        if not line:
            if printed:
                console.print()
            continue

        heading = parse_heading(line, allowed_headings)
        if heading in allowed_headings:
            if printed:
                console.print()
            console.print(Text(heading, style="bold cyan"))
            printed = True
            continue

        console.print(Text(format_body_line(line), style="green"))
        printed = True


def parse_heading(line: str, headings=None):
    headings = headings or SECTION_HEADINGS
    cleaned = re.sub(r"^\s*\d+[\).]\s*", "", line).strip()
    cleaned = cleaned.strip("*_# ").rstrip(":").strip()
    return cleaned if cleaned in headings else None


def parse_known_heading(line: str):
    return parse_heading(line, SECTION_HEADINGS)


def format_body_line(line: str) -> str:
    bullet_match = re.match(r"^([-*]\s+)(.*)", line)
    if bullet_match:
        bullet, body = bullet_match.groups()
        return fill(
            body,
            width=86,
            initial_indent=f"{bullet}",
            subsequent_indent="  ",
        )

    return fill(line, width=88)


def clean_ai_output(output: str, allowed_headings=None) -> str:
    allowed_headings = allowed_headings or SECTION_HEADINGS
    cleaned_lines = []
    seen_headings = set()
    skip_section = False
    in_code_block = False
    kept_code_block = False

    for raw_line in output.strip().splitlines():
        line = raw_line.rstrip()
        known_heading = parse_known_heading(line.strip())

        if known_heading:
            if known_heading not in allowed_headings or known_heading in seen_headings:
                skip_section = True
                continue
            seen_headings.add(known_heading)
            skip_section = False

        if skip_section:
            continue

        if line.strip().startswith("```"):
            if kept_code_block and not in_code_block:
                skip_section = True
                continue
            in_code_block = not in_code_block
            cleaned_lines.append(line)
            if not in_code_block:
                kept_code_block = True
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


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


def read_code_file(file_path: str):
    path, suggestion = find_project_file(file_path)
    if path is None:
        show_file_not_found(suggestion)
        return None

    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError):
        console.print("Could not read this file safely.", style="bold red")
        return None


def explain_code(file_path: str):
    code = read_code_file(file_path)
    if code is None:
        return

    prompt = f"{RESPONSE_RULES}\n{EXPLAIN_CODE_RULES}\nCode:\n\n{code}"
    render_ai_output(ask_llm(prompt), EXPLAIN_SECTION_HEADINGS)


def review(file_path: str):
    code = read_code_file(file_path)
    if code is None:
        return

    prompt = f"{RESPONSE_RULES}\n{REVIEW_RULES}\nCode:\n\n{code}"
    render_ai_output(
        ask_llm(prompt),
        REVIEW_SECTION_HEADINGS,
        default_heading="Code Quality Issues",
    )


def fix_bug(file_path: str):
    with open(file_path, "r") as f:
        error = f.read()

    prompt = f"{RESPONSE_RULES}\nFix this error:\n\n{error}"
    render_ai_output(ask_llm(prompt))
