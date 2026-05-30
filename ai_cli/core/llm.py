import requests


def trim_code(code: str, max_chars: int = 8000):
    return code[:max_chars]


def print_debug(message: str, fallback: str | None = None):
    try:
        print(message)
    except UnicodeEncodeError:
        print(fallback or message.encode("ascii", "ignore").decode().strip())


def _post_to_ollama(url: str, prompt: str, model: str):
    return requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 2048,
            },
        },
        timeout=120,
    )


def generate_response(prompt: str, model: str = "phi"):
    url = "http://127.0.0.1:11434/api/generate"

    print_debug("⏳ Sending request to Ollama...", "Sending request to Ollama...")

    try:
        try:
            response = _post_to_ollama(url, prompt, model)
        except requests.exceptions.Timeout:
            response = _post_to_ollama(url, trim_code(prompt), model)

        response.raise_for_status()

        data = response.json()

        if "response" not in data:
            print("Invalid response:", data)
            return "Error: Invalid response from model"

        return data["response"]

    except requests.exceptions.Timeout:
        return "Error: Model is slow (likely first run or large input). Try again or use smaller file."

    except Exception as e:
        print("DEBUG ERROR:", str(e))
        return f"Error: {str(e)}"
