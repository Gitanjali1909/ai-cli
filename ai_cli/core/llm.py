import requests

def ask_llm(prompt):
    res = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "phi",
            "prompt": prompt,
            "stream": False
        }
    )

    response = res.json()
    return response["response"]
