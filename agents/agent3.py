# agents/agent3.py
import os
import re
import json
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from models.dynamic_record import DynamicRecord
from tools.search import get_search_tool
from agents._react import run_react_loop

load_dotenv()

llm = ChatGroq(
    model=os.getenv("AGENT3_MODEL"),
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
INTERDICTIONS ABSOLUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Ne compare PAS les lignes entre elles
❌ Ne juge PAS les dates
❌ Ne juge PAS les valeurs NULL/NaN
❌ Ne juge PAS les formats numériques
❌ Ne juge PAS l'orthographe des valeurs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE (JSON UNIQUEMENT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "results": [
    {
      "row_index": 0,
      "is_valid": true,
      "score": 1.0,
      "reasoning": "raisonnement",
      "errors": [],
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


def extract_json_qwen(text: str) -> list:
    """Extrait JSON en gérant le bloc <think> de Qwen."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Pas de JSON trouvé")

    json_text = text[start:end+1]
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        for suffix in [']}', ']}]}']:
            try:
                data = json.loads(json_text + suffix)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise ValueError("JSON invalide même après réparation")

    results = data.get("results", [])
    for r in results:
        normalized = []
        for err in r.get("errors", []):
            if isinstance(err, str):
                normalized.append({
                    "field": "unknown",
                    "message": err,
                    "severity": "medium"
                })
            elif isinstance(err, dict):
                normalized.append({
                    "field": err.get("field", "unknown"),
                    "message": err.get("message",
                               err.get("error", "erreur inconnue")),
                    "severity": err.get("severity", "medium")
                })
        r["errors"] = normalized
    return results


def analyze_batch(
    records: list[DynamicRecord],
    max_retries: int = 3,
) -> list[dict]:
    """Analyse ligne par ligne pour Qwen."""
    all_results = []

    for record in records:
        batch_text = f"\n--- Ligne {record.row_index} ---\n"
        batch_text += record.to_prompt_text()

        user_prompt = f"""Analyse la cohérence de cette ligne :

{batch_text}

Retourne UNIQUEMENT le JSON avec la clé "results"."""

        use_search = needs_search([record])

        for attempt in range(max_retries):
            try:
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]

                if use_search:
                    content = run_react_loop(
                        llm_with_tools, search_tool,
                        messages, max_iterations=2
                    )
                    results = extract_json_qwen(content)
                else:
                    response = llm.invoke(messages)
                    results = extract_json_qwen(response.content)

                for r in results:
                    r["agent"] = "Agent3_Qwen32B"
                all_results.extend(results)
                time.sleep(0.5)
                break

            except Exception as e:
                error_msg = str(e)
                if "413" in error_msg and use_search:
                    print(f"⚠️  Agent3 413 → retry sans search")
                    use_search = False
                    continue
                if "429" in error_msg:
                    wait = 10 * (attempt + 1)
                    print(f"⏳ Agent3 rate limit — attente {wait}s")
                    time.sleep(wait)
                    continue
                all_results.append({
                    "agent": "Agent3_Qwen32B",
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