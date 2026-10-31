"""Operations Manager (runs every 10 minutes, 24/7): checks the live website, keeps the free host awake,
and triggers an automatic redeploy if it stays down. Never prints secrets."""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
if not BASE:
    print("::warning::PUBLIC_BASE_URL not set; nothing to monitor")
    raise SystemExit(0)


def healthy() -> bool:
    for _ in range(3):
        try:
            with urllib.request.urlopen(BASE + "/healthz", timeout=70) as r:  # long timeout: free hosts wake slowly
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(15)
    return False


def telegram(text: str) -> None:
    t, c = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if t and c:
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{t}/sendMessage", method="POST",
                data=json.dumps({"chat_id": c, "text": text}).encode(), headers={"Content-Type": "application/json"}), timeout=20)
        except Exception:
            pass


def redeploy() -> str:
    key = os.environ.get("RENDER_API_KEY")
    if not key:
        return "no Render key available"
    def call(method, path, body=None):
        req = urllib.request.Request("https://api.render.com/v1" + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": "Bearer " + key, "Accept": "application/json", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"null")
    try:
        found = call("GET", "/services?name=" + os.environ.get("RENDER_SERVICE_NAME", "sterling-vance") + "&limit=5")
        sid = found[0]["service"]["id"]
        call("POST", f"/services/{sid}/deploys", {"clearCache": "do_not_clear"})
        return "redeploy triggered"
    except Exception as e:
        return "redeploy failed: " + type(e).__name__


if healthy():
    print("::notice title=ops::site healthy")
else:
    result = redeploy()
    print("::warning title=ops::site DOWN, " + result)
    telegram(f"Operations Manager: {BASE} did not answer after 3 tries. Action: {result}.")
