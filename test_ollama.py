import requests

def ask_ai(prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "deepseek-coder:6.7b-instruct",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=data)
    response.raise_for_status()

    result = response.json()
    return result.get("response", "")

error_log = "TypeError: Cannot read property username of undefined"
prompt = f"Analyze this error and suggest a fix:\n{error_log}"

print(ask_ai(prompt))
