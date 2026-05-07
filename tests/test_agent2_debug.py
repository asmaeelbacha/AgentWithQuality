# test_agent2_debug.py
import sys, os
sys.path.insert(0, '.')
import requests
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
model = os.getenv("AGENT2_MODEL")

r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    },
    json={
        "model": model,
        "messages": [
            {"role": "system", "content": "Réponds uniquement en JSON"},
            {"role": "user", "content": "Dis juste {\"ok\": true}"}
        ],
        "max_tokens": 50
    },
    timeout=30
)
print(f"Status : {r.status_code}")
print(f"Réponse complète : {r.json()}")
content = r.json()["choices"][0]["message"]["content"]
print(f"\nContent type : {type(content)}")
print(f"Content : {repr(content)}")