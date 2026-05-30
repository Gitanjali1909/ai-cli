BASE_RULES = """
Rules:
- Do not hallucinate.
- Only use the given input.
- Do not mention files, libraries, functions, behavior, or context not present in the input.
- If something is unclear, say "Not clear from input".
- Be concise and structured.
"""


def explain_prompt(code: str) -> str:
    return f"""
You are a senior Python developer.

Explain the following code STRICTLY based on the given input.

Rules:
- Do NOT assume anything not present in the code
- Do NOT call it a chatbot unless clearly visible
- Be precise and technical
- Keep it clear and structured

Format:

1. What this code does (1-2 lines)
2. Key parts (bullet points)
3. Flow of execution (step-by-step)
4. Simple explanation (for beginner)

Code:
{code}
"""


def fix_prompt(error: str) -> str:
    return f"""
Fix or diagnose this input.

Output ONLY these sections:
Overview
Issues
Suggestions
Improved Code

{BASE_RULES}
- Focus on the error or broken code shown.
- Include a small improved snippet only when useful.

Input:
{error}
"""


def review_prompt(code: str) -> str:
    return f"""
Review this code like a senior developer reviewing a PR.

Output ONLY these sections:
Overview
Issues
Suggestions
Improved Code

{BASE_RULES}
- List real bugs only. Do not include vague or generic suggestions.
- Every issue must reference something visible in the input.
- Suggestions must be specific and actionable.
- Improved Code must include a concrete snippet.
- If there are no real bugs, say "No real bugs found in the given code."

Code:
{code}
"""
