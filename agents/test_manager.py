# agents/manager.py
import json
import time
from typing import TypedDict
from langgraph.graph import StateGraph, END
from models.dynamic_record import DynamicRecord
import agents.agent1 as agent1
import agents.agent2 as agent2
import agents.agent3 as agent3

# ══════════════════════════════════════════
# STATE — partagé entre tous les nodes
# ══════════════════════════════════════════

class AgentState(TypedDict):
    records: list[DynamicRecord]      # lignes à analyser
    results_agent1: list[dict]        # résultats agent 1
    results_agent2: list[dict]        # résultats agent 2
    results_agent3: list[dict]        # résultats agent 3
    final_results: list[dict]         # résultats finaux

# ══════════════════════════════════════════
# NODES
# ══════════════════════════════════════════

def node_agent1(state: AgentState) -> AgentState:
    """Node Agent 1 — GPT-OSS 120B"""
    print("  🤖 Agent 1 en cours...")
    results = agent1.analyze_batch(state["records"])
    return {"results_agent1": results}

def node_agent2(state: AgentState) -> AgentState:
    """Node Agent 2 — Llama 70B"""
    print("  🤖 Agent 2 en cours...")
    results = agent2.analyze_batch(state["records"])
    return {"results_agent2": results}

# Dans manager.py
def node_agent3(state: AgentState) -> AgentState:
    """Node Agent 3 — Qwen 32B — sous-batches de 2"""
    print("  🤖 Agent 3 en cours...")
    all_results = []
    records = state["records"]
    
    # Qwen a limite tokens → sous-batches de 2
    for i in range(0, len(records), 2):
        sub_batch = records[i:i+2]
        results = agent3.analyze_batch(sub_batch)
        all_results.extend(results)
        time.sleep(1)
    
    return {"results_agent3": all_results}

def node_aggregate(state: AgentState) -> AgentState:
    """
    Node Manager — compare les 3 résultats
    et décide le verdict final.
    """
    print("  📊 Agrégation des résultats...")

    r1_list = state["results_agent1"]
    r2_list = state["results_agent2"]
    r3_list = state["results_agent3"]

    # Indexe les résultats par row_index
    r1 = {r["row_index"]: r for r in r1_list}
    r2 = {r["row_index"]: r for r in r2_list}
    r3 = {r["row_index"]: r for r in r3_list}

    final_results = []
    all_indices = set(r1.keys()) | set(r2.keys()) | set(r3.keys())

    for idx in sorted(all_indices):
        res1 = r1.get(idx, {})
        res2 = r2.get(idx, {})
        res3 = r3.get(idx, {})

        # Score pondéré
        score1 = res1.get("score", 0.0)
        score2 = res2.get("score", 0.0)
        score3 = res3.get("score", 0.0)

        final_score = (
            score1 * 0.40 +  
            score2 * 0.35 +  
            score3 * 0.25    
        )

        # Vote majoritaire
        votes_valid = sum([
            1 if res1.get("is_valid", False) else 0,
            1 if res2.get("is_valid", False) else 0,
            1 if res3.get("is_valid", False) else 0,
        ])

        # Verdict final
        if votes_valid == 3:
            verdict = "CERTAIN_VALID"
        elif votes_valid == 2:
            verdict = "PROBABLY_VALID"
        elif votes_valid == 1:
            verdict = "PROBABLY_INVALID"
        else:
            verdict = "CERTAIN_INVALID"

        is_valid = votes_valid >= 2  # majorité

        # Collecte toutes les erreurs
        all_errors = (
            res1.get("errors", []) +
            res2.get("errors", []) +
            res3.get("errors", [])
        )

        final_results.append({
            "row_index": idx,
            "verdict": verdict,
            "is_valid": is_valid,
            "final_score": round(final_score, 4),
            "votes_valid": votes_valid,
            "scores": {
                "agent1": score1,
                "agent2": score2,
                "agent3": score3,
            },
            "all_errors": all_errors,
            "summaries": {
                "agent1": res1.get("summary", ""),
                "agent2": res2.get("summary", ""),
                "agent3": res3.get("summary", ""),
            }
        })

    return {"final_results": final_results}

# ══════════════════════════════════════════
# GRAPH LANGGRAPH
# ══════════════════════════════════════════

def build_graph():
    """Construit le graph LangGraph."""
    graph = StateGraph(AgentState)

    # Ajoute les nodes
    graph.add_node("agent1", node_agent1)
    graph.add_node("agent2", node_agent2)
    graph.add_node("agent3", node_agent3)
    graph.add_node("aggregate", node_aggregate)

    # Définit le flow
    graph.set_entry_point("agent1")
    graph.add_edge("agent1", "agent2")
    graph.add_edge("agent2", "agent3")
    graph.add_edge("agent3", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()

# Instance globale du graph
quality_graph = build_graph()

# ══════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════

def analyze_batch(records: list[DynamicRecord]) -> list[dict]:
    """
    Analyse un batch avec les 3 agents
    et retourne les résultats agrégés.
    """
    initial_state = {
        "records": records,
        "results_agent1": [],
        "results_agent2": [],
        "results_agent3": [],
        "final_results": [],
    }

    final_state = quality_graph.invoke(initial_state)
    return final_state["final_results"]