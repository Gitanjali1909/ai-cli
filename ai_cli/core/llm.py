import time
import requests


def trim_code(code: str, max_chars: int = 8000) -> str:
    return code[:max_chars]


def print_debug(message: str, fallback: str | None = None) -> None:
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


def generate_response(prompt: str, model: str = "phi") -> str:
    url = "http://127.0.0.1:11434/api/generate"
    max_retries = 3
    retry_delay = 2

    print_debug("⏳ Sending request to Ollama...", "Sending request to Ollama...")

    current_prompt = prompt
    for attempt in range(max_retries):
        try:
            try:
                response = _post_to_ollama(url, current_prompt, model)
            except requests.exceptions.Timeout:
                # If a single chunk times out, truncate aggressively and try one more time
                print_debug("⚠️ Chunk request timed out. Truncating context size...", "Chunk timed out. Truncating...")
                current_prompt = trim_code(current_prompt, max(1, int(len(current_prompt) * 0.5)))
                response = _post_to_ollama(url, current_prompt, model)

            response.raise_for_status()
            data = response.json()

            if "response" not in data:
                print("Invalid response:", data)
                return "Error: Invalid response from model"

            return data["response"]

        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            if attempt < max_retries - 1:
                print_debug(f"⚠️ Connection/HTTP error: {e}. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            print("DEBUG ERROR:", str(e))
            return f"Error: {str(e)}"

        except requests.exceptions.Timeout:
            # If the fallback request also times out, retry in the next loop iteration with the already truncated prompt
            if attempt < max_retries - 1:
                print_debug(f"⚠️ Timeout error. Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            return "Error: Model execution timed out on this chunk due to large context or cold boot."

        except Exception as e:
            print("DEBUG ERROR:", str(e))
            return f"Error: {str(e)}"
            
    return "Error: Maximum retries exceeded"