# agents/agent2.py
import os
import json
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from models.dynamic_record import DynamicRecord
from tools.search import get_search_tool
from agents._react import extract_json, run_react_loop

load_dotenv()

llm = ChatGroq(
    model=os.getenv("AGENT2_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=4000,
    temperature=0,
)

search_tool = get_search_tool(max_results=2)
llm_with_tools = llm.bind_tools([search_tool])

SYSTEM_PROMPT = """Tu es un Expert en Audit de Données Sémantiques.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TES 4 VÉRIFICATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. VALEUR DANS LA BONNE COLONNE
2. POLLUTION DE SCRAPING
3. ENTITÉS INCOMPATIBLES
4. CONTEXTE MÉTIER IRRÉALISTE

Tu as accès à un outil de recherche web.
Utilise-le UNIQUEMENT pour vérifier check 3.
N'utilise PAS l'outil pour formats numériques,
dates, ou incohérences évidentes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE FINAL (JSON UNIQUEMENT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "results": [
    {
      "row_index": 0,
      "is_valid": boolean,
      "score": float (0.0 à 1.0),
      "reasoning": "raisonnement",
      "errors": [
        {
          "field": "nom_colonne",
          "message": "description",
          "severity": "critical|high|medium|low",
          "type": "wrong_column|scraping_pollution|incompatible_entity|logical_contradiction|unrealistic_value"
        }
      ],
      "summary": "bilan"
    }
  ]
}

SCORE : 1.0=aucune | 0.8=low | 0.6=medium | 0.4=high | 0.2=critical
is_valid = true si score >= 0.6
Réponds UNIQUEMENT en JSON."""


def needs_search(records: list[DynamicRecord]) -> bool:
    """Détermine si le batch nécessite une recherche web."""
    for record in records:
        data = record.data
        power = str(data.get("Power", "") or "").strip()
        if power and not power.replace(".", "").replace(",", "").isdigit():
            return False
        fuel = str(data.get("Fuel", "") or "").strip().lower()
        known_fuels = {"electric", "diesel", "petrol", "hybrid",
                       "benzin", "gasolina", "elétrico", "híbrido",
                       "normal", "mild hybrid"}
        if fuel and fuel not in known_fuels:
            return False
        seats = data.get("Seats", None)
        try:
            if seats and float(str(seats)) > 10:
                return False
        except (ValueError, TypeError):
            pass
    return True


def analyze_batch(
    records: list[DynamicRecord],
    max_retries: int = 3,
) -> list[dict]:
    """Analyse un batch — sous-batches de 2."""
    all_results = []

    for i in range(0, len(records), 2):
        sub_batch = records[i:i+2]
        batch_text = ""
        for record in sub_batch:
            batch_text += f"\n--- Ligne {record.row_index} ---\n"
            batch_text += record.to_prompt_text()
            batch_text += "\n"

        user_prompt = f"""Analyse la cohérence de ces lignes :

{batch_text}

Retourne un objet JSON avec une clé "results"."""

        use_search = needs_search(sub_batch)

        for attempt in range(max_retries):
            try:
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]

                if use_search:
                    content = run_react_loop(
                        llm_with_tools, search_tool,
                        messages, max_iterations=3
                    )
                    results = extract_json(content)
                else:
                    response = llm.invoke(messages)
                    results = extract_json(response.content)

                for r in results:
                    r["agent"] = "Agent2_Llama70B"
                all_results.extend(results)
                time.sleep(1)
                break

            except Exception as e:
                error_msg = str(e)
                if "413" in error_msg and use_search:
                    print(f"⚠️  Agent2 413 → retry sans search")
                    use_search = False
                    continue
                if "429" in error_msg:
                    wait = 10 * (attempt + 1)
                    print(f"⏳ Agent2 rate limit — attente {wait}s")
                    time.sleep(wait)
                    continue
                all_results.extend([{
                    "agent": "Agent2_Llama70B",
                    "row_index": r.row_index,
                    "is_valid": False,
                    "score": 0.0,
                    "errors": [{"field": "api",
                               "message": error_msg[:100],
                               "severity": "critical"}],
                    "summary": "Erreur API"
                } for r in sub_batch])
                break

    return all_results