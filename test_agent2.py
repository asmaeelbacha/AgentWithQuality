# test_agent2.py
from tools.csv_loader import load_batches
from agents.agent2 import analyze_batch

print("🚀 Test Agent 2\n")

for batch in load_batches(
    "C:/Users/INTERN I/Desktop/quality_agent/data/PT_B2C_LYS_OFF.xlsx",
    batch_size=5,
    max_records=5,
):
    print(f"📦 Analyse de {len(batch)} lignes...\n")
    results = analyze_batch(batch)

    for r in results:
        status = "✅" if r["is_valid"] else "❌"
        print(f"{status} Ligne {r['row_index']} "
              f"| Score: {r['score']} "
              f"| {r['summary']}")
        if r["errors"]:
            for err in r["errors"]:
                print(f"   └─ [{err['severity']}] "
                      f"{err['field']}: {err['message']}")
    break