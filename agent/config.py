"""Central configuration. Everything is overridable via environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "sales.db"))
LOG_DIR = Path(os.getenv("LOG_DIR", ROOT / "logs"))
PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()  # "anthropic" or "google"
_DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-6", "google": "gemini-2.5-flash"}
MODEL = os.getenv("LLM_MODEL", _DEFAULT_MODELS.get(PROVIDER, ""))
EVAL_DELAY_S = float(os.getenv("EVAL_DELAY_S", "0"))  # pause between eval questions (free-tier rate limits)
MAX_STEPS = int(os.getenv("MAX_STEPS", "12"))  # LangGraph recursion limit
