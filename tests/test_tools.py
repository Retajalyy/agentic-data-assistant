import pytest

from agent import config
from agent.tools import api_tool, db_tool
from data.seed_db import seed


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    seed(path)
    monkeypatch.setattr(config, "DB_PATH", path)


def test_select_works():
    res = db_tool.execute_readonly("SELECT COUNT(*) FROM customers")
    assert res["rows"] == [(40,)]


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders", "DROP TABLE orders", "SELECT 1; DELETE FROM orders",
    "UPDATE orders SET quantity=0", "PRAGMA table_info(orders)",
])
def test_writes_are_rejected(sql):
    assert db_tool.query_database.invoke({"sql": sql}).startswith("ERROR")


def test_schema_lists_tables():
    schema = db_tool.get_schema()
    assert all(t in schema for t in ("customers", "products", "orders"))


def test_exchange_rate_tool_handles_api_failure(monkeypatch):
    def boom(*a, **k):
        raise api_tool.requests.ConnectionError("offline")
    monkeypatch.setattr(api_tool.requests, "get", boom)
    out = api_tool.get_exchange_rate.invoke({"base": "USD", "target": "EUR"})
    assert out.startswith("ERROR")
