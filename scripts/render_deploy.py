"""Creates (or updates) the Render web service for this repo, deploys it, waits until it is live, prints the URL.
Runs inside GitHub Actions. Never prints secrets."""
import json
import os
import sys
import time
import urllib.error
import urllib.request

KEY = os.environ["RENDER_API_KEY"]
NAME = os.environ.get("RENDER_SERVICE_NAME", "sterling-vance")
REPO = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "yomide01/sterling-vance-partners")
API = "https://api.render.com/v1"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + KEY, "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]


def die(msg, detail=""):
    print("FAILED:", msg, detail)
    sys.exit(1)


st, owners = call("GET", "/owners?limit=5")
if st != 200 or not owners:
    die("could not list Render owners (is the API key valid?)", f"{st} {owners}")
owner_id = owners[0]["owner"]["id"]
print("owner ok")

st, found = call("GET", "/services?name=" + NAME + "&limit=20")
svc = next((x["service"] for x in (found or []) if isinstance(found, list) and x["service"]["name"] == NAME), None)

env = {"PUBLIC_BASE_URL": "https://%s.onrender.com" % NAME, "PRICE": os.environ.get("PRICE") or "15000", "CURRENCY": os.environ.get("CURRENCY") or "NGN"}
for k in ("PAYSTACK_SECRET_KEY", "SUPPORT_EMAIL", "STATS_TOKEN"):
    if os.environ.get(k):
        env[k] = os.environ[k]

if not svc:
    body = {"type": "web_service", "name": NAME, "ownerId": owner_id, "repo": REPO, "branch": "main", "autoDeploy": "yes",
            "serviceDetails": {"runtime": "python", "plan": "free", "region": "oregon", "healthCheckPath": "/healthz",
                               "envSpecificDetails": {"buildCommand": "echo no build needed", "startCommand": "python app.py"}},
            "envVars": [{"key": k, "value": v} for k, v in env.items()]}
    st, res = call("POST", "/services", body)
    if st not in (200, 201):
        die("could not create the service", f"{st} {res}")
    svc = res["service"]
    print("service created")
else:
    print("service already exists")

sid = svc["id"]
url = (svc.get("serviceDetails") or {}).get("url") or "https://%s.onrender.com" % NAME
if env["PUBLIC_BASE_URL"] != url:
    env["PUBLIC_BASE_URL"] = url
st, cur = call("GET", "/services/%s/env-vars" % sid)
existing = {e["envVar"]["key"]: e["envVar"].get("value") for e in (cur or []) if isinstance(cur, list)}
merged = {**existing, **env}
if merged != existing:
    st, res = call("PUT", "/services/%s/env-vars" % sid, [{"key": k, "value": v} for k, v in merged.items() if v is not None])
    print("env vars updated" if st in (200, 201) else "env update problem: %s %s" % (st, res))
    call("POST", "/services/%s/deploys" % sid, {"clearCache": "do_not_clear"})

print("waiting for deploy...")
status = ""
for _ in range(60):
    time.sleep(10)
    st, ds = call("GET", "/services/%s/deploys?limit=1" % sid)
    status = (ds[0]["deploy"]["status"] if isinstance(ds, list) and ds else "unknown")
    print(" status:", status)
    if status in ("live", "build_failed", "update_failed", "canceled", "deactivated"):
        break
if status != "live":
    die("deploy did not go live", status)

for _ in range(12):
    try:
        with urllib.request.urlopen(url + "/healthz", timeout=30) as r:
            if r.status == 200:
                print("HEALTHY at", url)
                print("RENDER_URL=" + url)
                print("::notice title=Render URL::" + url)
                sys.exit(0)
    except Exception:
        time.sleep(10)
die("deployed but health check not answering", url)
