
from tools.csv_loader import load_batches

for batch in load_batches(
    "C:/Users/INTERN I/Desktop/quality_agent/data/PT_B2C_LYS_OFF.xlsx",
    batch_size=10,
    max_records=20, 
):
    print(f"\n── Premier record du batch ──")
    print(batch[0].to_prompt_text())
    print("─" * 40)