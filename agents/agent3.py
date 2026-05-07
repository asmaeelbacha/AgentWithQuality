# agents/agent3.py
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from models.dynamic_record import DynamicRecord
from agents._react import extract_json

load_dotenv()

MODEL = os.getenv("AGENT3_MODEL", "anthropic/claude-haiku-latest")
API_KEY = os.getenv("OPENROUTER_API_KEY")



SYSTEM_PROMPT = """Tu es un Expert en Audit de Données Sémantiques.
Ton rôle est de vérifier la LOGIQUE et la COHÉRENCE des données.
Python gère déjà les types et formats — toi tu analyses le SENS.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE FONDAMENTALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tu analyses CHAQUE LIGNE INDÉPENDAMMENT.
Tu n'as AUCUNE connaissance des autres lignes.
Tu ne fais JAMAIS de comparaison entre lignes.
Tu utilises UNIQUEMENT les données fournies.
Tu n'utilises PAS tes connaissances externes
sur les modèles de voitures ou le marché.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TES 4 VÉRIFICATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. VALEUR DANS LA BONNE COLONNE :
   ❌ colonne "fuel" contient "30.000 km"
   ❌ colonne "price" contient "rouge"
   ❌ colonne "make" contient "En stock"

2. POLLUTION DE SCRAPING :
   ❌ colonne "model" contient "Livraison gratuite"
   ❌ colonne "version" contient "Cliquez ici"

3. ENTITÉS INCOMPATIBLES :
   ❌ make = "BMW" model = "Clio"
   ❌ fuel = "Électrique" version = "TDI diesel"

4. CONTEXTE MÉTIER IRRÉALISTE :
   ❌ Seats = 20 pour une voiture
   ❌ Price = 0 ou négatif

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERDICTIONS ABSOLUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Ne compare PAS les lignes entre elles
❌ Ne juge PAS les dates
   → La date d'aujourd'hui est fournie
   → Toute date passée ou récente = valide
❌ Ne juge PAS les valeurs NULL/NaN
❌ Ne juge PAS les formats numériques
   → "30.000 km" = format européen valide
   → "100.000 kr" = format norvégien valide
   → "5.0" = entier pandas valide
❌ Ne juge PAS les unités et majuscules
   → "kwh" et "kWh" = pareil → valide
❌ Ne juge PAS si un modèle existe
   → Bénéfice du doute → valide
❌ Ne juge PAS si une version existe
   → "LRDM", "RS", "Evolve" → valide
❌ Ne juge PAS le type de carrosserie
❌ Ne signale PAS [long_text] comme erreur
❌ Ne juge PAS les prix
   → Sauf si price = 0 ou négatif

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE (JSON UNIQUEMENT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "results": [
    {
      "row_index": 0,
      "is_valid": boolean,
      "score": float (0.0 à 1.0),
      "reasoning": "Raisonnement basé UNIQUEMENT sur cette ligne",
      "errors": [
        {
          "field": "nom_colonne",
          "message": "Description précise",
          "severity": "critical|high|medium|low",
          "type": "wrong_column|scraping_pollution|incompatible_entity|logical_contradiction|unrealistic_value"
        }
      ],
      "summary": "Bilan en une phrase"
    }
  ]
}

SCORE :
1.0 = aucune incohérence
0.8 = low | 0.6 = medium
0.4 = high | 0.2 = critical
is_valid = true si score >= 0.6

Réponds UNIQUEMENT en JSON.

"""


def call_llm(messages: list, max_tokens: int = 2000) -> str:
    """Appel direct OpenRouter."""
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def analyze_batch(
    records: list[DynamicRecord],
    max_retries: int = 3,
) -> list[dict]:
    """Analyse 1 ligne à la fois."""
    all_results = []

    for record in records:
        batch_text = f"\n--- Ligne {record.row_index} ---\n"
        batch_text += record.to_prompt_text()
        today = datetime.now().strftime("%d/%m/%Y")

        user_prompt = f"""Date d'aujourd'hui : {today}

Analyse la cohérence de cette ligne :

{batch_text}

Retourne un objet JSON avec une clé "results"."""

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
                content = call_llm(messages)
                
                results = extract_json(content)
                for r in results:
                    r["agent"] = "Agent3_HaikuLatest"
                all_results.extend(results)
                time.sleep(0.5)
                break

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    wait = 10 * (attempt + 1)
                    print(f"⏳ Agent3 rate limit — attente {wait}s")
                    time.sleep(wait)
                    continue
                all_results.append({
                    "agent": "Agent3_HaikuLatest",
                    "row_index": record.row_index,
                    "is_valid": False,
                    "score": 0.0,
                    "errors": [{"field": "api",
                               "message": error_msg[:100],
                               "severity": "critical"}],
                    "summary": "Erreur API"
                })
                break

    return all_results