# test_qwen_debug.py
import os
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

llm = ChatGroq(
    model=os.getenv("AGENT3_MODEL", "qwen/qwen3-32b"),
    api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=4000,
    temperature=0,
)

response = llm.invoke([
    SystemMessage(content="""Tu es un Expert en Audit de Données Sémantiques.
Réponds UNIQUEMENT en JSON valide.
{
  "results": [
    {
      "row_index": 0,
      "is_valid": true,
      "score": 1.0,
      "reasoning": "...",
      "errors": [],
      "summary": "..."
    }
  ]
}"""),
    HumanMessage(content="""Analyse cette ligne :
  Make_model: Polestar 2
  Fuel: Elétrico
  Power: 421
  emissions: 0 g/km

Réponds UNIQUEMENT en JSON."""),
])

print("=== RÉPONSE COMPLÈTE ===")
print(response.content)
print("\n=== APRÈS SUPPRESSION THINK ===")
text = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()
print(repr(text[:300]))