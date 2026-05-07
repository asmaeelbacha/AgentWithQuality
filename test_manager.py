# test_manager.py
import os
import time
from tools.csv_loader import load_batches
from agents.test_manager import analyze_batch

print("🚀 Test Manager LangGraph\n")

FILEPATH = "C:/Users/INTERN I/Desktop/quality_agent/data/Exemple2.xlsx"

file_results = []

for batch in load_batches(
    FILEPATH,
    batch_size=10,
    max_records=10,
):
    print(f"📦 Analyse de {len(batch)} lignes...")
    results = analyze_batch(batch)
    file_results.extend(results)
    time.sleep(2)

valid = sum(1 for r in file_results if r["is_valid"])
invalid = len(file_results) - valid
print(f"\n📊 Résumé : {valid} valides / {invalid} invalides\n")

for r in file_results:
    status = "✅" if r["is_valid"] else "❌"
    print(f"\n{status} Ligne {r['row_index']}")
    print(f"   Verdict     : {r['verdict']}")
    print(f"   Score final : {r['final_score']}")
    print(f"   Votes valid : {r['votes_valid']}/3")
    print(f"   Scores      : "
          f"A1={r['scores']['agent1']} | "
          f"A2={r['scores']['agent2']} | "
          f"A3={r['scores']['agent3']}")
    if r["all_errors"]:
        print(f"   Erreurs ({len(r['all_errors'])}) :")
        for err in r["all_errors"]:
            field = err.get('field', '')
            severity = err.get('severity', '?')
            message = err.get('message', '')
            if field and field != 'unknown':
                print(f"   └─ [{severity}] [{field}] {message}")
            else:
                print(f"   └─ [{severity}] {message}")

print("\n✅ Traitement terminé !")