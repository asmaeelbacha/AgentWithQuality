
from tools.csv_loader import load_batches
from agents.test_manager import analyze_batch

print("🚀 Test Manager LangGraph\n")

for batch in load_batches(
    "C:/Users/INTERN I/Desktop/quality_agent/data/exemple2.xlsx",
    batch_size=10,     
    max_records=10,    
):
    print(f"📦 Analyse de {len(batch)} lignes...\n")
    results = analyze_batch(batch)

    print("\n" + "="*50)
    print("RÉSULTATS FINAUX")
    print("="*50)

    valid = sum(1 for r in results if r["is_valid"])
    invalid = len(results) - valid

    print(f"\n📊 Résumé : {valid} valides / {invalid} invalides\n")

    for r in results:
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
            for err in r["all_errors"][:3]:
                print(f"   └─ [{err.get('severity','?')}] "
                      f"{err.get('message','')[:70]}")
    