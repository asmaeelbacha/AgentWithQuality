# test_groq_models.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

response = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

models = response.json()["data"]

print(f"=== {len(models)} MODÈLES DISPONIBLES SUR GROQ ===\n")
for m in models:
    print(f"  {m['id']}")