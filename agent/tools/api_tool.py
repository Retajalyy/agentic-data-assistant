"""REST API tool: live currency exchange rates from the free Frankfurter API (no key needed)."""
import json

import requests
from langchain_core.tools import tool

BASE_URL = "https://api.frankfurter.app"


def fetch_rate(base: str, target: str, date: str = "latest") -> dict:
    resp = requests.get(
        f"{BASE_URL}/{date}",
        params={"from": base.upper(), "to": target.upper()},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


@tool
def get_exchange_rate(base: str, target: str, date: str = "latest") -> str:
    """Get the exchange rate from `base` to `target` currency (ISO codes, e.g. USD, EUR).
    `date` is 'latest' or YYYY-MM-DD. The sales database stores all amounts in USD."""
    try:
        return json.dumps(fetch_rate(base, target, date))
    except requests.RequestException as exc:
        return f"ERROR: exchange-rate API call failed: {exc}"
