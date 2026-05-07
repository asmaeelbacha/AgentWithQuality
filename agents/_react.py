# agents/_react.py
import re
import json


def extract_json(text: str) -> list:
    """
    Extrait et parse le JSON retourné par le LLM.
    Gère les formats : {"results": [...]} ou [...]
    """
    # Supprime <think> blocks (Qwen)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()

    # Cherche liste ou objet JSON
    start_obj = text.find("{")
    start_list = text.find("[")

    if start_list != -1 and (start_obj == -1 or start_list < start_obj):
        end = text.rfind("]")
        json_text = text[start_list:end+1]
    elif start_obj != -1:
        end = text.rfind("}")
        json_text = text[start_obj:end+1]
    else:
        raise ValueError("Pas de JSON trouvé")

    # Parse JSON
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        for suffix in [']}', ']}]}', ']}]}]}']:
            try:
                data = json.loads(json_text + suffix)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise ValueError("JSON invalide même après réparation")

    # Gère les 2 formats possibles
    if isinstance(data, list):
        results = data
    elif isinstance(data, dict):
        results = data.get("results", [])
    else:
        raise ValueError("Format JSON non reconnu")

    # ← FIX : nouvelle liste qui exclut les strings
    final_results = []
    for r in results:
        if not isinstance(r, dict):
            continue  # ← ignore les strings
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
                    "severity": err.get("severity", "medium"),
                    "type": err.get("type", "unknown"),
                })
        r["errors"] = normalized
        final_results.append(r)  # ← ajoute seulement les dicts

    return final_results  # ← retourne seulement les dicts ✅