"""Structured JSONL logging of every LLM call and tool call (for debugging and evaluation)."""
import json
import logging
import time
from datetime import datetime, timezone

from langchain_core.callbacks import BaseCallbackHandler

from agent import config

logger = logging.getLogger("agent")


def setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler(config.LOG_DIR / "agent.jsonl"))
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    logger.addHandler(console)


def _emit(event: str, **fields) -> None:
    record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    logger.info(json.dumps(record, default=str))


class JsonlCallback(BaseCallbackHandler):
    """Logs tool calls with latency and LLM token usage."""

    def __init__(self) -> None:
        self._starts: dict = {}

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self._starts[run_id] = time.perf_counter()
        _emit("tool_start", tool=serialized.get("name"), input=input_str)

    def on_tool_end(self, output, *, run_id, **kwargs):
        ms = (time.perf_counter() - self._starts.pop(run_id, time.perf_counter())) * 1000
        _emit("tool_end", latency_ms=round(ms, 1), output=str(output)[:500])

    def on_tool_error(self, error, *, run_id, **kwargs):
        _emit("tool_error", error=str(error))

    def on_llm_end(self, response, **kwargs):
        usage = {}
        try:
            usage = response.generations[0][0].message.usage_metadata or {}
        except (AttributeError, IndexError):
            pass
        _emit("llm_end", usage=usage)
