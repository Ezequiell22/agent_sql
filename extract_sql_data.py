import json
import os
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from config import get_engine, get_allowed_tables

_ = load_dotenv(find_dotenv())

engine = get_engine()

def list_tables():
    allowed = get_allowed_tables()
    if allowed:
        return allowed
    q = """
    SELECT TOP 50 TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA='dbo'
    ORDER BY TABLE_NAME
    """
    rows = pd.read_sql_query(q, engine)
    return [r["TABLE_NAME"] for _, r in rows.iterrows()]


os.makedirs("dataset", exist_ok=True)
with open("dataset/sql_schema.jsonl", "w", encoding="utf-8") as f:
    for tabela in list_tables():
        try:
            print(f"🔎 Processando {tabela}...")
            df = pd.read_sql(f"SELECT TOP 10000 * FROM {tabela}", engine)
            schema = [{"column": col, "dtype": str(df[col].dtype)} for col in df.columns]

            def convert_row(row):
                new_row = {}
                for k, v in row.items():
                    if pd.isna(v):
                        new_row[k] = ""
                    elif isinstance(v, pd.Timestamp):
                        new_row[k] = v.isoformat()
                    else:
                        new_row[k] = v
                return new_row

            example_rows = [convert_row(row) for row in df.head(5).to_dict(orient="records")]

            doc = {
                "table": tabela,
                "schema": schema,
                "examples": example_rows
            }

            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f" Erro em {tabela}: {e}")
