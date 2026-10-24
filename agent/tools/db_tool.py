"""Read-only SQL tools. Safety is enforced twice: a query validator and a read-only connection."""
import re
import sqlite3

from langchain_core.tools import tool

from agent import config

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|vacuum)\b", re.I
)


def _connect() -> sqlite3.Connection:
    # mode=ro makes the database physically read-only for this connection
    return sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)


def validate_sql(sql: str) -> str:
    """Return the cleaned query or raise ValueError if it is not a single SELECT."""
    cleaned = sql.strip().rstrip(";").strip()
    if ";" in cleaned:
        raise ValueError("Only a single statement is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(cleaned):
        raise ValueError("Query contains a forbidden keyword; the database is read-only.")
    return cleaned


def get_schema() -> str:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return "\n\n".join(sql for _, sql in rows)


def execute_readonly(sql: str, max_rows: int = 50) -> dict:
    query = validate_sql(sql)
    with _connect() as conn:
        cur = conn.execute(query)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchmany(max_rows + 1)
    truncated = len(rows) > max_rows
    return {"columns": cols, "rows": rows[:max_rows], "truncated": truncated}


@tool
def describe_database() -> str:
    """Return the CREATE TABLE statements of the sales database. Call this before writing SQL."""
    return get_schema()


@tool
def query_database(sql: str) -> str:
    """Run a single read-only SQLite SELECT query against the sales database and return the rows.
    Revenue = quantity * unit_price for orders with status = 'completed'."""
    try:
        result = execute_readonly(sql)
    except (ValueError, sqlite3.Error) as exc:
        return f"ERROR: {exc}"
    return str(result)
