# find_working_models.py
import os
import time
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

# Récupère tous les modèles gratuits depuis l'API
print("🔍 Récupération des modèles gratuits...\n")
response = requests.get(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

all_models = response.json()["data"]

# Filtre les modèles gratuits
free_models = [
    m["id"] for m in all_models
    if ":free" in m["id"]
]

print(f"✅ {len(free_models)} modèles gratuits trouvés\n")
print("─" * 50)

# Teste TOUS les modèles
working = []
rate_limited = []
not_available = []

for model in free_models:
    try:
        print(f"  Test : {model} ...")
        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=10,
            timeout=15,
        )
        llm.invoke("Say OK")
        print(f"  ✅ FONCTIONNE\n")
        working.append(model)
        time.sleep(2)  # pause pour éviter rate limit

    except Exception as e:
        error = str(e)
        if "429" in error:
            print(f"  ⏳ Rate limited\n")
            rate_limited.append(model)
        elif "404" in error:
            print(f"  ❌ Non disponible\n")
            not_available.append(model)
        elif "402" in error:
            print(f"  💳 Crédits requis\n")
        else:
            print(f"  ❌ Erreur : {error[:60]}\n")
        time.sleep(1)

# Rapport final
print("\n" + "=" * 50)
print("📊 RAPPORT FINAL")
print("=" * 50)

print(f"\n✅ MODÈLES QUI FONCTIONNENT ({len(working)}) :")
for i, m in enumerate(working, 1):
    print(f"  {i}. {m}")

print(f"\n⏳ RATE LIMITED ({len(rate_limited)}) :")
for m in rate_limited:
    print(f"  → {m}")

print(f"\n❌ NON DISPONIBLES ({len(not_available)}) :")
for m in not_available:
    print(f"  → {m}")

print(f"\n💡 RECOMMANDATION POUR TES 3 AGENTS :")
if len(working) >= 3:
    print(f"  AGENT1_MODEL={working[0]}")
    print(f"  AGENT2_MODEL={working[1]}")
    print(f"  AGENT3_MODEL={working[2]}")
elif len(working) == 2:
    print(f"  AGENT1_MODEL={working[0]}")
    print(f"  AGENT2_MODEL={working[1]}")
    print(f"  AGENT3_MODEL=??? (aucun 3ème disponible)")
else:
    print("  ⚠️ Pas assez de modèles disponibles")
    print("  → Attends 15 minutes et réessaie")