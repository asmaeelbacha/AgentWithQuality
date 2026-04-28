# tools/csv_loader.py
import math
import pandas as pd
from typing import Generator
from models.dynamic_record import DynamicRecord

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage basique avant envoi aux agents.
    """
    original_count = len(df)

    # 1. Supprime les lignes entièrement vides
    df = df.dropna(how="all")

    # 2. Supprime les doublons exacts
    df = df.drop_duplicates()

    # 3. Réinitialise l'index
    df = df.reset_index(drop=True)

    # 4. Supprime les espaces dans les colonnes texte
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # 5. Remplace les chaînes vides par None
    df = df.replace("", None)

    # 6. ← NOUVEAU : Tronque les colonnes à texte long
    for col in df.select_dtypes(include="object").columns:
        try:
            avg_len = df[col].dropna().apply(len).mean()
            if avg_len > 150:
                df[col] = df[col].apply(
                    lambda x: "[long_text]" if pd.notna(x) else x
                )
                print(f"✂️  Colonne tronquée : {col} "
                      f"(moyenne {avg_len:.0f} chars)")
        except Exception:
            continue

    cleaned_count = len(df)
    removed = original_count - cleaned_count

    if removed > 0:
        print(f"🧹 Nettoyage : {removed} lignes supprimées "
              f"({original_count} → {cleaned_count})")
    else:
        print(f"🧹 Nettoyage : données déjà propres "
              f"({cleaned_count} lignes)")

    return df


def load_batches(
    filepath: str,
    batch_size: int = 10,
    max_records: int = None,
) -> Generator[list[DynamicRecord], None, None]:
    """
    Lit n'importe quel fichier Excel/CSV,
    nettoie les données et yielde des batches.
    """
    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath)
    else:
        df = pd.read_csv(filepath)

    if max_records:
        df = df.head(max_records)

    df = df.where(pd.notna(df), None)
    df = clean_dataframe(df)

    print(f"✅ Fichier : {len(df)} lignes, "
          f"{len(df.columns)} colonnes")
    print(f"📋 Colonnes : {list(df.columns)}\n")

    total_batches = math.ceil(len(df) / batch_size)

    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i + batch_size]
        records = []
        for idx, row in batch_df.iterrows():
            records.append(DynamicRecord(
                data=row.to_dict(),
                row_index=idx,
                source_file=filepath,
            ))
        batch_num = (i // batch_size) + 1
        print(f"📦 Batch {batch_num}/{total_batches} "
              f"— {len(records)} lignes")
        yield records