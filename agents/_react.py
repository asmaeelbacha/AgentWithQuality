import re
import json
from langchain_core.messages import ToolMessage


def extract_json(text: str) -> list:
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
        for suffix in [']}', ']}]}', ']}]}]}']:
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
                normalized.append({"field": "unknown", "message": err, "severity": "medium"})
            elif isinstance(err, dict):
                normalized.append({
                    "field": err.get("field", "unknown"),
                    "message": err.get("message", err.get("error", "erreur inconnue")),
                    "severity": err.get("severity", "medium"),
                    "type": err.get("type", "unknown"),
                })
        r["errors"] = normalized

    return results


def run_react_loop(llm_with_tools, search_tool, messages, max_iterations: int = 5) -> str:
    for _ in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tc in response.tool_calls:
            try:
                result = search_tool.invoke(tc["args"])
                content = str(result)[:800]
            except Exception as e:
                content = f"Erreur recherche: {str(e)[:100]}"

            messages.append(ToolMessage(
                content=content,
                tool_call_id=tc["id"],
            ))

    return messages[-2].content if len(messages) >= 2 else ""
