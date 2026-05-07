# test_raw_agents.py
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

for agent_name, model_env in [
    ("Agent 1", "AGENT1_MODEL"),
    ("Agent 2", "AGENT2_MODEL"),
]:
    print(f"\n{'='*50}")
    print(f"TEST {agent_name} — {os.getenv(model_env)}")
    print('='*50)

    llm = ChatGroq(
        model=os.getenv(model_env),
        api_key=os.getenv("GROQ_API_KEY"),
        max_tokens=2000,
        temperature=0,
    )

    response = llm.invoke([
        SystemMessage(content="Réponds UNIQUEMENT en JSON valide."),
        HumanMessage(content="""Analyse ces 2 lignes.
Retourne UNIQUEMENT cette liste JSON sans aucun texte :
[
  {"row_index": 0, "is_valid": true, "score": 0.95, "errors": [], "summary": "résumé"},
  {"row_index": 1, "is_valid": true, "score": 0.95, "errors": [], "summary": "résumé"}
]

Ligne 0: make_model=FIAT Grande Panda, fuel=Electrique, price=159
Ligne 1: make_model=Jeep Avenger, fuel=Hybride, price=199"""),
    ])

    print(f"Réponse brute :")
    print(repr(response.content[:300]))
    print(f"\nTexte :")
    print(response.content[:300])