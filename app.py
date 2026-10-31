"""Web server (standard library only, so it runs free anywhere). Run: python app.py"""
import io
import json
import mimetypes
import threading
import time
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import hmac
from company import auditor, config, fixes, metrics, payments, publisher, site
from company.agents import ceo as ceo_agent
from company.safe_fetch import FetchError, normalize_url

_hits: dict = {}
_cache: dict = {}
_lock = threading.Lock()
_slots = threading.Semaphore(4)  # at most 4 audits at once (free hosting is small)


def rate_ok(ip: str, limit: int = 12, window: int = 3600) -> bool:
    now = time.time()
    with _lock:
        hits = [t for t in _hits.get(ip, []) if now - t < window]
        if len(hits) >= limit:
            _hits[ip] = hits
            return False
        hits.append(now)
        _hits[ip] = hits
        return True


def run_audit(url: str) -> dict:
    key = normalize_url(url)
    with _lock:
        c = _cache.get(key)
        if c and time.time() - c[0] < 600:
            return c[1]
    with _slots:
        a = auditor.audit(key)
    metrics.hit("audit")
    with _lock:
        if len(_cache) > 500:
            _cache.clear()
        _cache[key] = (time.time(), a)
    return a


class Handler(BaseHTTPRequestHandler):
    server_version = "SV/2.0"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _ip(self):
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self._send(200, site.home())
            if u.path == "/about":
                return self._send(200, site.about())
            if u.path == "/healthz":
                metrics.hit("health")
                return self._send(200, "ok", "text/plain")
            if u.path == "/team":
                return self._send(200, site.team())
            if u.path in ("/stats", "/dashboard"):
                return self._admin(u.path, q)
            if u.path == "/audit":
                if not rate_ok(self._ip()):
                    return self._send(429, site.message("Slow down", "Too many checks from your network this hour. Please try again later."))
                a = run_audit(q.get("url", ""))
                return self._send(200, site.audit_page(a, payments.enabled()))
            if u.path in ("/thanks", "/pack.zip"):
                return self._paid(u.path, q.get("reference") or q.get("trxref", ""))
            return self._static(u.path)
        except (FetchError, auditor.AuditError) as e:
            return self._send(200, site.message("We couldn't check that website", str(e)))
        except Exception:
            return self._send(500, site.message("Something went wrong", "Please try again in a minute."))

    def _admin(self, path, q):
        tok = (self.headers.get("Authorization", "")[7:] or q.get("token", ""))
        if not config.STATS_TOKEN or not hmac.compare_digest(tok, config.STATS_TOKEN):
            return self._send(404, site.message("Page not found", "That page doesn't exist."))
        if path == "/stats":
            return self._send(200, json.dumps(metrics.snapshot()), "application/json")
        rep = {}
        f = config.REPORTS / "last_cycle.json"
        if f.exists():
            rep = json.loads(f.read_text())
        money = None
        if payments.enabled():
            try:
                money = payments.revenue_last_days(30)
            except Exception:
                pass
        rv = config.REPORTS / "weekly_review.md"
        return self._send(200, site.dashboard({"metrics": metrics.snapshot(), "report": rep, "money": money, "guides": len(publisher.all_guides()),
                                               "review": rv.read_text() if rv.exists() else ""}), extra={"Cache-Control": "no-store"})

    def _paid(self, path, ref):
        if not payments.enabled():
            return self._send(404, site.message("Not available", "Payments are not switched on yet."))
        ok = payments.verify(ref)
        if not ok:
            return self._send(402, site.message("Payment not confirmed", "We couldn't confirm that payment. If you were charged, email us with your receipt and we will sort it out."))
        a = auditor.audit(ok["site"])
        metrics.hit("paid_unlocks")
        pack = fixes.build_pack(a)
        if path == "/pack.zip":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for n, c in pack.items():
                    z.writestr(n, c)
            return self._send(200, buf.getvalue(), "application/zip", {"Content-Disposition": 'attachment; filename="fix-pack.zip"'})
        return self._send(200, site.pack_page(a, pack, ref))

    def do_POST(self):
        n = min(int(self.headers.get("Content-Length") or 0), 20000)
        raw = self.rfile.read(n)
        try:
            if self.path == "/webhook/paystack":
                if not payments.enabled() or not payments.valid_signature(raw, self.headers.get("x-paystack-signature", "")):
                    return self._send(401, "bad signature", "text/plain")
                return self._send(200, "ok", "text/plain")  # fulfilment is pull-based (verified on /thanks), nothing to store
            if self.path == "/checkout":
                f = {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode()).items()}
                email, url = f.get("email", "").strip(), normalize_url(f.get("url", ""))
                if "@" not in email or len(email) > 120 or not payments.enabled():
                    return self._send(400, site.message("Check your details", "Please enter a valid email address."))
                if not rate_ok(self._ip(), 20):
                    return self._send(429, site.message("Slow down", "Please try again later."))
                loc = payments.init_checkout(email, url)
                metrics.hit("checkout_started")
                return self._send(303, "", "text/plain", {"Location": loc})
        except FetchError as e:
            return self._send(400, site.message("Check your details", str(e)))
        except Exception:
            return self._send(500, site.message("Something went wrong", "Please try again in a minute."))
        return self._send(404, "not found", "text/plain")

    def _static(self, path):
        rel = urllib.parse.unquote(path).lstrip("/") or "index.html"
        if rel.endswith("/"):
            rel += "index.html"
        f = (config.PUBLIC / rel).resolve()
        if config.PUBLIC.resolve() not in f.parents or not f.is_file():
            return self._send(404, site.message("Page not found", "That page doesn't exist."))
        if rel.startswith("guides/") and rel.endswith(".html") and f.name != "index.html":
            metrics.hit("guide_view", f.stem)
        ctype = mimetypes.guess_type(f.name)[0] or "text/plain"
        return self._send(200, f.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text") or "xml" in ctype else ""),
                          {"Cache-Control": "public, max-age=300"})


if __name__ == "__main__":
    print(f"{config.BRAND} running on http://0.0.0.0:{config.PORT}  (payments {'ON' if payments.enabled() else 'OFF'})")
    ThreadingHTTPServer(("0.0.0.0", config.PORT), Handler).serve_forever()
