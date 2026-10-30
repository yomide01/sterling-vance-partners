"""Reporter agent: tells the founder what happened (Telegram if configured) and saves a report file (no secrets)."""
import json
import time
import urllib.request

from .. import config


def save(report: dict) -> None:
    config.REPORTS.mkdir(parents=True, exist_ok=True)
    (config.REPORTS / "last_cycle.json").write_text(json.dumps(report, indent=2))


def telegram(text: str) -> bool:
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        return False
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage", method="POST",
                                     data=json.dumps({"chat_id": config.TELEGRAM_CHAT_ID, "text": text[:3800]}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=20).read()
        return True
    except Exception:
        return False


def summary(r: dict) -> str:
    rev = r.get("money") or {}
    money = (f"Last 30 days: {rev.get('sales', 0)} sales, {rev.get('currency', '')} {rev.get('revenue', 0):,}"
             if rev else "Revenue: payments not connected yet")
    return (f"Daily report {r['date']}\nNew guides published: {len(r['published'])}\nRejected by quality check: {len(r['rejected'])}\n"
            f"Total guides live: {r['total_guides']}\n{money}\n{r.get('ceo_note', '')}")
