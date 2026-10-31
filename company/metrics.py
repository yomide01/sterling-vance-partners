"""Live counters (no personal data stored: no IPs, no emails, no site contents). Reset when the server restarts;
the CEO snapshots them into data/metrics.json every day so history survives."""
import secrets
import threading
import time

_lock = threading.Lock()
BOOT_ID = secrets.token_hex(4)
_boot = time.time()
_c = {"audits": 0, "checkout_started": 0, "paid_unlocks": 0, "guide_views": {}, "last_audit": 0, "last_health_ping": 0, "health_pings": 0}


def hit(kind: str, key: str = None) -> None:
    with _lock:
        if kind == "guide_view" and key:
            _c["guide_views"][key] = _c["guide_views"].get(key, 0) + 1
        elif kind == "audit":
            _c["audits"] += 1; _c["last_audit"] = time.time()
        elif kind == "health":
            _c["health_pings"] += 1; _c["last_health_ping"] = time.time()
        elif kind in _c:
            _c[kind] += 1


def snapshot() -> dict:
    with _lock:
        return {"boot_id": BOOT_ID, "uptime_s": int(time.time() - _boot), "audits": _c["audits"], "checkout_started": _c["checkout_started"],
                "paid_unlocks": _c["paid_unlocks"], "guide_views": dict(_c["guide_views"]), "last_audit": int(_c["last_audit"]),
                "last_health_ping": int(_c["last_health_ping"]), "health_pings": _c["health_pings"]}
