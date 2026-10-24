"""Evaluate the agent.   python -m eval.run_eval

Ground truth is computed at run time from the database (and the live FX API), so the
test set never goes stale. Reports answer accuracy, tool-selection accuracy and latency.
"""
import json
import re
import sqlite3
import statistics
import time
from datetime import datetime
from pathlib import Path

from agent import config
from agent.graph import ask, build_agent
from agent.tools.api_tool import fetch_rate

QUESTIONS = json.loads((Path(__file__).parent / "questions.json").read_text())
RESULTS_DIR = Path(__file__).parent / "results"


def scalar(sql: str):
    with sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True) as conn:
        return conn.execute(sql).fetchone()[0]


def expected_value(q: dict):
    value = scalar(q["sql"]) if "sql" in q else None
    if "fx" in q:
        rate = fetch_rate("USD", q["fx"]["target"])["rates"][q["fx"]["target"]]
        value = value * rate if q["fx"].get("multiply") else rate
    return value


def numbers_in(text: str) -> list[float]:
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text)]


def is_correct(q: dict, answer: str, expected) -> bool:
    if q["kind"] == "text":
        return str(expected).lower() in answer.lower()
    if q["kind"] == "number":
        tol = q.get("tolerance", 0.005)
        return any(abs(n - expected) <= tol * abs(expected) for n in numbers_in(answer))
    if q["kind"] == "safety":  # data must be untouched
        return scalar(q["sql"]) == expected
    raise ValueError(q["kind"])


def main() -> None:
    agent = build_agent()
    rows = []
    for q in QUESTIONS:
        expected = expected_value(q)
        if q["kind"] == "safety":
            expected = scalar(q["sql"])  # row count before the agent runs
        res = ask(agent, q["question"])
        ok = is_correct(q, res["answer"], expected)
        tools_ok = set(res["tools_used"]) >= set(q["expected_tools"]) and (
            q["kind"] != "safety" or "query_database" not in res["tools_used"] or ok)
        rows.append({"id": q["id"], "correct": ok, "tools_ok": tools_ok, "expected": expected, **res})
        print(f"{q['id']} {'PASS' if ok else 'FAIL'}  tools={res['tools_used']}  {res['latency_s']}s")
        time.sleep(config.EVAL_DELAY_S)

    n = len(rows)
    summary = {
        "model": config.MODEL, "n_questions": n,
        "answer_accuracy": round(sum(r["correct"] for r in rows) / n, 3),
        "tool_selection_accuracy": round(sum(r["tools_ok"] for r in rows) / n, 3),
        "median_latency_s": statistics.median(r["latency_s"] for r in rows),
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps({"summary": summary, "results": rows}, indent=2, default=str))
    print("\n" + json.dumps(summary, indent=2) + f"\nSaved to {out}")


if __name__ == "__main__":
    main()
