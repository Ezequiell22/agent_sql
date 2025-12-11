import os
from typing import List, Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv(find_dotenv())


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável de ambiente ausente: {name}")
    return value


def get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def get_allowed_tables() -> Optional[List[str]]:
    raw = os.getenv("ALLOWED_TABLES")
    if not raw:
        return None
    return [t.strip() for t in raw.split(",") if t.strip()]


def build_odbc_connection_string() -> str:
    driver = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")
    server = require_env("SERVER_DB")
    database = require_env("DATABASE")
    user = require_env("USER_DB")
    password = require_env("PASS_DB")
    odbc_str = quote_plus(
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
    )
    return f"mssql+pyodbc:///?odbc_connect={odbc_str}"


def get_engine() -> Engine:
    return create_engine(build_odbc_connection_string())

