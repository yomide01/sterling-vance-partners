"""Paystack payments. The paid state is always re-verified with Paystack, so no database is needed
and nobody can unlock the pack by editing a URL."""
import hashlib
import hmac
import json
import time
import urllib.request
from typing import Any, Dict, Optional

from . import config

_API = "https://api.paystack.co"


def enabled() -> bool:
    return bool(config.PAYSTACK_SECRET_KEY)


def _call(method: str, path: str, body: Optional[dict] = None) -> Dict[str, Any]:
    req = urllib.request.Request(_API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + config.PAYSTACK_SECRET_KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def init_checkout(email: str, site: str, call=_call) -> str:
    res = call("POST", "/transaction/initialize", {
        "email": email, "amount": config.PRICE * 100, "currency": config.CURRENCY,
        "callback_url": config.BASE_URL + "/thanks", "metadata": {"site": site, "product": "ai-visibility-fix-pack"}})
    return res["data"]["authorization_url"]


def verify(reference: str, call=_call) -> Optional[Dict[str, Any]]:
    """Returns {'site':..., 'email':...} only if Paystack confirms a successful payment of at least the price."""
    if not reference or not reference.replace("-", "").replace("_", "").isalnum():
        return None
    d = call("GET", "/transaction/verify/" + reference).get("data", {})
    if d.get("status") != "success" or d.get("amount", 0) < config.PRICE * 100 or d.get("currency") != config.CURRENCY:
        return None
    site = (d.get("metadata") or {}).get("site")
    return {"site": site, "email": (d.get("customer") or {}).get("email", "")} if site else None


def valid_signature(raw_body: bytes, header: str) -> bool:
    mac = hmac.new(config.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return bool(header) and hmac.compare_digest(mac, header)


def revenue_last_days(days: int = 30, call=_call) -> Dict[str, Any]:
    """Source of truth for the CEO's numbers: Paystack itself."""
    since = time.strftime("%Y-%m-%dT00:00:00.000Z", time.gmtime(time.time() - days * 86400))
    d = call("GET", "/transaction?status=success&perPage=100&from=" + since).get("data", [])
    rows = [t for t in d if t.get("currency") == config.CURRENCY]
    return {"sales": len(rows), "revenue": sum(t.get("amount", 0) for t in rows) // 100, "currency": config.CURRENCY}
