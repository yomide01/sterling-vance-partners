import hashlib, hmac, json, os, re, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

os.environ["PAYSTACK_SECRET_KEY"] = "sk_test_unit"
os.environ["PUBLIC_BASE_URL"] = "https://example.test"
from company import auditor, config, fixes, payments, publisher, site
from company.agents import guardian, quality, research
from company.safe_fetch import FetchError, fetch, normalize_url

GOOD = """<!doctype html><html lang="en"><head><title>Bright Smile Dental | Dentist in Lagos</title>
<meta name="description" content="Family dentist in Lagos offering check-ups, whitening and braces. Book online or call today.">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta property="og:site_name" content="Bright Smile Dental">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Dentist","name":"Bright Smile Dental","telephone":"+234 801 234 5678","address":{"@type":"PostalAddress","streetAddress":"1 Test Rd"}}</script></head>
<body><h1>Bright Smile Dental</h1><a href="tel:+2348012345678">Call us</a><a href="/book">Book an appointment</a><a href="/services">Services</a>
<img src="a.jpg" alt="Clinic"><p>%s</p></body></html>""" % ("We provide friendly dental care for the whole family. " * 30)
BAD = "<html><head></head><body><p>hi</p><img src='x.png'></body></html>"
ROBOTS_BAD = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow: /admin\n"


def make_server(pages):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            if self.path in pages:
                b = pages[self.path].encode()
                self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            elif self.path == "/redir":
                self.send_response(302); self.send_header("Location", "/"); self.end_headers()
            else:
                self.send_response(404); self.end_headers()
    s = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, "http://127.0.0.1:%d" % s.server_port


class SafeFetch(unittest.TestCase):
    def test_blocks_private_and_bad_urls(self):
        for u in ["http://127.0.0.1/", "http://localhost/", "http://169.254.169.254/latest/meta-data/", "http://10.0.0.1/", "ftp://example.com", "javascript:alert(1)"]:
            with self.assertRaises(FetchError, msg=u): fetch(u)

    def test_normalize(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com/")
        with self.assertRaises(FetchError): normalize_url("")
        with self.assertRaises(FetchError): normalize_url("nodots")


class Auditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = make_server({"/": GOOD, "/llms.txt": "# x", "/robots.txt": "User-agent: *\nAllow: /\n", "/sitemap.xml": "<urlset/>"})
        cls.bsrv, cls.bbase = make_server({"/": BAD, "/robots.txt": ROBOTS_BAD})

    def test_good_site_scores_high_with_real_findings(self):
        a = auditor.audit(self.base + "/", allow_private=True)
        ids = {c["id"]: c["status"] for c in a["checks"]}
        self.assertGreaterEqual(a["score"], 85)
        for k in ("schema", "schema_detail", "bots", "llms", "sitemap", "phone", "cta", "mobile"): self.assertEqual(ids[k], "pass", k)
        self.assertEqual(a["profile"]["name"], "Bright Smile Dental")
        self.assertEqual(a["profile"]["local_type"], "Dentist")

    def test_bad_site_scores_low_and_detects_blocked_bot(self):
        a = auditor.audit(self.bbase + "/", allow_private=True)
        ids = {c["id"]: c["status"] for c in a["checks"]}
        self.assertLess(a["score"], 35)
        self.assertEqual(ids["bots"], "fail"); self.assertIn("GPTBot", a["blocked_bots"])
        self.assertNotIn("ClaudeBot", a["blocked_bots"])  # only the bot with an explicit rule is blocked
        self.assertEqual(ids["schema"], "fail"); self.assertEqual(ids["phone"], "fail")

    def test_robots_wildcard_block(self):
        self.assertEqual(set(auditor._robots_blocked("User-agent: *\nDisallow: /\n")), set(auditor.AI_BOTS))
        self.assertEqual(auditor._robots_blocked("User-agent: *\nDisallow: /admin\n"), [])

    def test_unreachable(self):
        with self.assertRaises(auditor.AuditError): auditor.audit("http://127.0.0.1:1/")  # private blocked by default


class Fixes(unittest.TestCase):
    def test_pack_uses_real_data_and_marks_blanks(self):
        srv, base = make_server({"/": BAD.replace("<p>hi</p>", "<h1>Joe Plumbing</h1>")})
        a = auditor.audit(base + "/", allow_private=True)
        pack = fixes.build_pack(a)
        self.assertEqual(set(pack), {"1-structured-data.html", "2-llms.txt", "3-robots-fix.txt", "4-title-and-description.html", "5-install-guide.txt"})
        ld = json.loads(re.search(r">(.*)</script>", pack["1-structured-data.html"], re.S).group(1))
        self.assertEqual(ld["@type"], "LocalBusiness")
        self.assertIn("FILL IN", json.dumps(ld))               # nothing invented
        self.assertNotIn("aggregateRating", json.dumps(ld))    # no fake ratings, ever
        self.assertTrue(pack["2-llms.txt"].startswith("# "))

    def test_robots_fix_names_blocked_bots(self):
        srv, base = make_server({"/": GOOD, "/robots.txt": ROBOTS_BAD})
        a = auditor.audit(base + "/", allow_private=True)
        self.assertIn("User-agent: GPTBot", fixes.build_robots_fix(a))


class Payments(unittest.TestCase):
    def fake(self, status="success", amount=None, cur="NGN"):
        amt = config.PRICE * 100 if amount is None else amount
        return lambda m, p, b=None: {"data": {"status": status, "amount": amt, "currency": cur, "metadata": {"site": "https://x.com/"}, "customer": {"email": "a@b.co"}}}

    def test_verify(self):
        self.assertEqual(payments.verify("abc123", self.fake())["site"], "https://x.com/")
        self.assertIsNone(payments.verify("abc123", self.fake(status="failed")))
        self.assertIsNone(payments.verify("abc123", self.fake(amount=100)))      # underpaid
        self.assertIsNone(payments.verify("abc123", self.fake(cur="USD")))
        self.assertIsNone(payments.verify("../../etc", self.fake()))             # junk reference rejected

    def test_signature(self):
        body = b'{"event":"charge.success"}'
        good = hmac.new(b"sk_test_unit", body, hashlib.sha512).hexdigest()
        self.assertTrue(payments.valid_signature(body, good))
        self.assertFalse(payments.valid_signature(body, "deadbeef"))
        self.assertFalse(payments.valid_signature(body, ""))

    def test_revenue(self):
        r = payments.revenue_last_days(30, call=lambda m, p, b=None: {"data": [{"amount": 1500000, "currency": "NGN"}, {"amount": 500, "currency": "USD"}]})
        self.assertEqual((r["sales"], r["revenue"]), (1, 15000))


class Content(unittest.TestCase):
    def good_guide(self):
        return {"title": "t", "description": "d" * 80, "sections": [{"h2": "s%d" % i, "body": "word " * 200} for i in range(5)]}

    def test_quality_gate(self):
        self.assertTrue(quality.check(self.good_guide())[0])
        g = self.good_guide(); g["sections"][0]["body"] += " studies show 70% of people"
        self.assertFalse(quality.check(g)[0])
        g = self.good_guide(); g["sections"] = g["sections"][:2]
        self.assertFalse(quality.check(g)[0])
        g = self.good_guide(); g["sections"][1]["body"] += " we guarantee first place"
        self.assertFalse(quality.check(g)[0])

    def test_honest_disclaimers_allowed(self):
        g = self.good_guide(); g["sections"][0]["body"] += " Nobody can guarantee rankings, and we do not promise first place."
        self.assertTrue(quality.check(g)[0], quality.check(g)[1])
        g["sections"][0]["body"] += " We guarantee you will rank well."
        self.assertFalse(quality.check(g)[0])

    def test_everyday_phrases_not_flagged(self):
        g = self.good_guide(); g["sections"][0]["body"] += " Your Google Business Profile is often the first place AI assistants look."
        self.assertTrue(quality.check(g)[0], quality.check(g)[1])
        g["sections"][1]["body"] += " Do this and you will rank first on Google."
        self.assertFalse(quality.check(g)[0])

    def test_research_skips_existing(self):
        t = research.next_topics({"dentists-ai-search"}, 2)
        self.assertEqual(len(t), 2); self.assertNotIn("dentists-ai-search", [x["slug"] for x in t])

    def test_html_is_escaped(self):
        a = {"final_url": "x", "score": 10, "grade": "D", "profile": {"name": "<script>alert(1)</script>"},
             "checks": [{"id": "a", "label": "<img src=x onerror=1>", "status": "fail", "detail": "<b>", "fix": "<i>", "weight": 1}]}
        out = site.audit_page(a, True)
        self.assertNotIn("<script>alert(1)</script>", out); self.assertNotIn("<img src=x", out)

    def test_seed_guides_published(self):
        self.assertGreaterEqual(len(publisher.all_guides()), 2)


class Guardian(unittest.TestCase):
    def test_forbidden_actions(self):
        for a in guardian.FORBIDDEN:
            with self.assertRaises(guardian.Violation): guardian.allow(a)
        self.assertTrue(guardian.allow("publish_guide"))

    def test_codebase_has_no_outreach_capability(self):
        banned = re.compile(r"smtplib|sendmail|email\.mime|api\.brevo|api\.resend|mailgun|sendgrid|twilio", re.I)
        for p in list(Path("company").rglob("*.py")) + [Path("app.py")]:
            self.assertIsNone(banned.search(p.read_text()), "%s contains outreach/email-sending code" % p)


if __name__ == "__main__":
    unittest.main()
