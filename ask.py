import re
import os
import json
import argparse
import pandas as pd
from typing import Dict, List, Optional, Tuple
from sqlalchemy.engine import Engine
from langchain_openai import ChatOpenAI
from config import get_engine, get_allowed_tables, get_openai_model


def fetch_schema(engine: Engine, tables: Optional[List[str]]) -> Dict[str, List[str]]:
    query = """
    SELECT TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo'
    """
    if tables:
        placeholders = ",".join([f"'{t}'" for t in tables])
        query += f" AND TABLE_NAME IN ({placeholders})"
    rows = pd.read_sql_query(query, engine)
    schema: Dict[str, List[str]] = {}
    for _, r in rows.iterrows():
        schema.setdefault(r["TABLE_NAME"], []).append(r["COLUMN_NAME"])
    return schema


def build_schema_text(schema: Dict[str, List[str]]) -> str:
    parts = []
    for table, cols in schema.items():
        parts.append(f"Tabela {table}: {', '.join(cols)}")
    return "\n".join(parts)


def sanitize_sql(sql: str) -> str:
    s = sql.strip().strip("`").strip()
    code_block = re.search(r"```sql(.*?)```", s, re.DOTALL | re.IGNORECASE)
    if code_block:
        s = code_block.group(1).strip()
    s = s.split(";")[0].strip()
    disallowed = ["UPDATE", "DELETE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "EXEC", "MERGE"]
    upper = s.upper()
    if not upper.startswith("SELECT"):
        raise RuntimeError("Somente consultas SELECT são permitidas")
    for kw in disallowed:
        if kw in upper:
            raise RuntimeError(f"Palavra-chave SQL não permitida: {kw}")
    return s


def enforce_row_limit(sql: str, limit: int) -> str:
    upper = sql.upper()
    if "TOP " in upper or "OFFSET" in upper or "FETCH" in upper:
        return sql
    return re.sub(r"(?i)^\\s*SELECT\\s+", f"SELECT TOP {limit} ", sql, count=1)

def extract_tables(sql: str) -> List[str]:
    found: List[str] = []
    for m in re.finditer(r"(?i)\\bFROM\\s+([\\w\\[\\]\\.]+)", sql):
        found.append(m.group(1).split(".")[-1].strip("[]"))
    for m in re.finditer(r"(?i)\\bJOIN\\s+([\\w\\[\\]\\.]+)", sql):
        found.append(m.group(1).split(".")[-1].strip("[]"))
    return list({t for t in found if t})

def validate_tables(sql: str, schema: Dict[str, List[str]], allowed: Optional[List[str]]) -> None:
    used = extract_tables(sql)
    keys = set(schema.keys())
    if allowed:
        allowed_set = set(allowed)
        for t in used:
            if t not in allowed_set:
                raise RuntimeError(f"Tabela não permitida na consulta: {t}")
    for t in used:
        if t not in keys:
            raise RuntimeError(f"Tabela desconhecida no esquema: {t}")

def generate_sql(question: str, schema_text: str, tables: Optional[List[str]]) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY ausente")
    llm = ChatOpenAI(model=get_openai_model(), temperature=0)
    system = (
        "Você é um assistente especializado em gerar SQL Server seguro e somente leitura. "
        "Use apenas tabelas e colunas fornecidas. Responda com APENAS a consulta SQL."
    )
    prompt = f"{system}\n\nEsquema disponível:\n{schema_text}\n\nPergunta:\n{question}"
    out = llm.predict(prompt)
    return sanitize_sql(out)


def summarize_dataframe(df: pd.DataFrame) -> Dict[str, str]:
    summary: Dict[str, str] = {}
    summary["linhas"] = str(len(df))
    summary["colunas"] = str(len(df.columns))
    numeric = df.select_dtypes(include=["number"])
    if not numeric.empty:
        desc = numeric.describe().to_dict()
        summary["estatisticas_numericas"] = str(desc)
    cat = df.select_dtypes(exclude=["number"])
    if not cat.empty:
        uniques = {c: int(cat[c].nunique()) for c in cat.columns}
        summary["valores_unicos"] = str(uniques)
    return summary


def run(question: str, limit: int, report: bool) -> Dict[str, object]:
    try:
        engine = get_engine()
        allowed = get_allowed_tables()
        schema = fetch_schema(engine, allowed)
        schema_text = build_schema_text(schema)
        sql = generate_sql(question, schema_text, allowed)
        validate_tables(sql, schema, allowed)
        sql_limited = enforce_row_limit(sql, limit)
        df = pd.read_sql_query(sql_limited, engine)
        summary = summarize_dataframe(df)
        result: Dict[str, object] = {
            "pergunta": question,
            "sql": sql_limited,
            "tabelas": list(df.columns),
            "amostra": df.head(min(20, len(df))).to_dict(orient="records"),
            "resumo": summary,
        }
        if report:
            result["relatorio"] = {"preview_csv": df.to_csv(index=False)[:50000]}
        return result
    except Exception as e:
        return {"erro": str(e), "pergunta": question}


def main():
    parser = argparse.ArgumentParser(description="Pergunte ao banco via SQL seguro")
    parser.add_argument("pergunta", type=str, help="Pergunta em linguagem natural")
    parser.add_argument("--limit", type=int, default=500, help="Limite de linhas retornadas")
    parser.add_argument("--report", action="store_true", help="Gera relatório resumido")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args()
    out = run(args.pergunta, args.limit, args.report)
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
        return
    if "erro" in out:
        print("Erro:", out["erro"])
        return
    print("Pergunta:", out["pergunta"])
    print("SQL:", out["sql"])
    print("Resumo:", out["resumo"])
    print("Amostra:")
    for row in out["amostra"]:
        print(row)
    if args.report and "relatorio" in out:
        print("Relatório:")
        print(out["relatorio"]["preview_csv"])


if __name__ == "__main__":
    main()
