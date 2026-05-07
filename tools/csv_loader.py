# tools/csv_loader.py
import math
import pandas as pd
from typing import Generator
from models.dynamic_record import DynamicRecord

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    original_count = len(df)
    df = df.dropna(how="all")
    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    df = df.replace("", None)
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
    max_records: int = 10,
) -> Generator[list[DynamicRecord], None, None]:

    if filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath)
    else:
        for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try:
                df = pd.read_csv(
                    filepath,
                    encoding=encoding,
                    on_bad_lines='skip',
                    sep=None,
                    engine='python'
                )
                print(f"✅ Encodage détecté : {encoding}")
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"Encodage inconnu : {filepath}")

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