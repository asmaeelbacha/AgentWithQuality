# agents/agent1.py
import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from models.dynamic_record import DynamicRecord
from tools.search import get_search_tool
from agents._react import extract_json, run_react_loop

load_dotenv()

llm = ChatGroq(
    model=os.getenv("AGENT1_MODEL", "openai/gpt-oss-120b"),
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

1. VALEUR DANS LA BONNE COLONNE :
   La valeur correspond-elle sémantiquement
   au nom de sa colonne ?

2. POLLUTION DE SCRAPING :
   Le champ contient-il du texte
   qui ne lui appartient pas ?

3. ENTITÉS INCOMPATIBLES :
   Les champs décrivant la même entité
   sont-ils cohérents entre eux ?

4. CONTEXTE MÉTIER IRRÉALISTE :
   Les valeurs sont-elles réalistes
   dans leur contexte ?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTIL DE RECHERCHE DISPONIBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tu as accès à un outil de recherche web.
Utilise-le UNIQUEMENT pour vérifier check 3 (entités incompatibles)
quand tu as un doute sur la cohérence entre champs.

Exemples de recherches utiles :
→ "BMW Clio car model" → cette combinaison marque/modèle existe ?
→ "FIAT Grande Panda electric version" → ce modèle existe en électrique ?
→ "Polestar 2 body type hatchback SUV" → quel est le type de carrosserie ?

N'utilise PAS l'outil pour :
→ Vérifier des formats numériques
→ Vérifier des dates
→ Des incohérences évidentes (ex: "Grand" dans une colonne Power)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE FINAL (JSON UNIQUEMENT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "results": [
    {
      "row_index": 0,
      "is_valid": boolean,
      "score": float (0.0 à 1.0),
      "reasoning": "Explique ton raisonnement basé UNIQUEMENT sur cette ligne",
      "errors": [
        {
          "field": "nom_colonne",
          "message": "Description précise de l'incohérence détectée",
          "severity": "critical|high|medium|low",
          "type": "wrong_column|scraping_pollution|incompatible_entity|logical_contradiction|unrealistic_value"
        }
      ],
      "summary": "Bilan de la ligne en une phrase"
    }
  ]
}

SCORE :
1.0 = aucune incohérence
0.8 = incohérences low
0.6 = incohérences medium
0.4 = incohérences high
0.2 = incohérences critical
is_valid = true si score >= 0.6

Réponds UNIQUEMENT en JSON."""


def needs_search(records: list[DynamicRecord]) -> bool:
    """
    Détermine si le batch nécessite une recherche web.
    Recherche SEULEMENT si aucune erreur évidente visible.
    """
    for record in records:
        data = record.data

        # Erreur évidente dans Power → pas besoin de search
        power = str(data.get("Power", "") or "").strip()
        if power and not power.replace(".", "").replace(",", "").isdigit():
            return False

        # Erreur évidente dans Fuel → pas besoin de search
        fuel = str(data.get("Fuel", "") or "").strip().lower()
        known_fuels = {"electric", "diesel", "petrol", "hybrid",
                       "benzin", "gasolina", "elétrico", "híbrido",
                       "normal", "mild hybrid"}
        if fuel and fuel not in known_fuels:
            return False

        # Seats irréaliste → pas besoin de search
        seats = data.get("Seats", None)
        try:
            if seats and float(str(seats)) > 10:
                return False
        except (ValueError, TypeError):
            pass

    return True  # Pas d'erreur évidente → search utile


def analyze_batch(
    records: list[DynamicRecord],
    max_retries: int = 3,
) -> list[dict]:
    """
    Analyse un batch avec search conditionnel.
    Search activé seulement si pas d'erreur évidente.
    """
    batch_text = ""
    for record in records:
        batch_text += f"\n--- Ligne {record.row_index} ---\n"
        batch_text += record.to_prompt_text()
        batch_text += "\n"

    user_prompt = f"""Analyse la cohérence de ces lignes :

{batch_text}

Retourne un objet JSON avec une clé "results" contenant la liste des analyses."""

    # Détermine si search nécessaire
    use_search = needs_search(records)

    for attempt in range(max_retries):
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            if use_search:
                # Avec search tool
                content = run_react_loop(
                    llm_with_tools,
                    search_tool,
                    messages,
                    max_iterations=3
                )
            else:
                # Sans search tool — appel direct
                response = llm.invoke(messages)
                content = response.content

            results = extract_json(content)
            for r in results:
                r["agent"] = "Agent1_GPT120B"
            return results

        except Exception as e:
            error_msg = str(e)

            # Si 413 → retry SANS search
            if "413" in error_msg and use_search:
                print(f"⚠️  Agent1 413 → retry sans search")
                use_search = False
                continue

            if "429" in error_msg:
                wait = 10 * (attempt + 1)
                print(f"⏳ Agent1 rate limit — attente {wait}s "
                      f"(tentative {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue

            return [{
                "agent": "Agent1_GPT120B",
                "row_index": r.row_index,
                "is_valid": False,
                "score": 0.0,
                "errors": [{"field": "api",
                           "message": error_msg[:100],
                           "severity": "critical"}],
                "summary": "Erreur API"
            } for r in records]

    return [{
        "agent": "Agent1_GPT120B",
        "row_index": r.row_index,
        "is_valid": False,
        "score": 0.0,
        "errors": [{"field": "api",
                   "message": "Max retries dépassé",
                   "severity": "critical"}],
        "summary": "Rate limit persistant"
    } for r in records]