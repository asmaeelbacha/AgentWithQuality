# test_debug.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
print(f"Clé : '{key[:20]}'")
print(f"Agent1 : '{os.getenv('AGENT1_MODEL')}'")
print(f"Agent2 : '{os.getenv('AGENT2_MODEL')}'")
print(f"Agent3 : '{os.getenv('AGENT3_MODEL')}'")

# Test Agent 1
r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    },
    json={
        "model": os.getenv("AGENT1_MODEL"),
        "messages": [{"role": "user", "content": "OK"}],
        "max_tokens": 10
    },
    timeout=30
)
print(f"\nAgent1 status : {r.status_code}")
print(f"Agent1 réponse : {r.json()}")