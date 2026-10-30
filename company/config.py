"""All settings come from environment variables (see .env.example). Nothing secret is stored in the code."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
REPORTS = ROOT / "data" / "reports"


def env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


BRAND = env("BRAND_NAME", "Sterling & Vance")
BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:4000").rstrip("/")
PORT = int(env("PORT", "4000"))

# Product / pricing (whole units of the currency, e.g. 15000 = NGN 15,000)
PRICE = int(env("PRICE", "15000"))
CURRENCY = env("CURRENCY", "NGN")

PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY")

GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")

# Company guardrails (the Guardian agent enforces these)
MAX_GUIDES_PER_DAY = int(env("MAX_GUIDES_PER_DAY", "2"))
MONTHLY_SPEND_LIMIT_USD = 0  # the company never spends money
