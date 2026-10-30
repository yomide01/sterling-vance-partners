"""The product's engine: a real audit of a real website. Every finding comes from the page we fetched."""
import json
import re
import time
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, List

from .safe_fetch import FetchError, fetch

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "ClaudeBot", "Google-Extended"]
LOCAL_TYPES = {"LocalBusiness", "Dentist", "Restaurant", "Store", "ProfessionalService", "LegalService", "Physician",
               "MedicalBusiness", "MedicalClinic", "Plumber", "Electrician", "RoofingContractor", "HVACBusiness",
               "AccountingService", "FinancialService", "RealEstateAgent", "BeautySalon", "HealthClub", "AutoRepair",
               "HomeAndConstructionBusiness", "GeneralContractor", "HairSalon", "DaySpa", "Hotel", "CafeOrCoffeeShop"}
CTA = re.compile(r"\b(book|schedule|appointment|get a quote|free quote|request (a )?(quote|estimate|call)|estimate|call (us|now)|contact us|reserve|order now)\b", re.I)
PHONE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?)?\d{3,4}[\s.-]\d{3,4}(?:[\s.-]\d{2,4})?")


class AuditError(Exception):
    pass


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""; self.in_title = False
        self.meta: Dict[str, str] = {}
        self.h1: List[str] = []; self.in_h1 = False
        self.links: List[tuple] = []; self._a = None; self._a_text = ""
        self.imgs = 0; self.imgs_alt = 0
        self.jsonld: List[str] = []; self.in_ld = False; self._ld = ""
        self.text: List[str] = []; self.skip = 0
        self.canonical = ""; self.lang = ""; self.buttons: List[str] = []; self._btn = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "html": self.lang = a.get("lang", "")
        elif tag == "title": self.in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key: self.meta[key] = a.get("content", "")
        elif tag == "link" and "canonical" in a.get("rel", "").lower(): self.canonical = a.get("href", "")
        elif tag == "h1": self.in_h1 = True; self.h1.append("")
        elif tag == "a": self._a = a.get("href", ""); self._a_text = ""
        elif tag == "img":
            self.imgs += 1
            if a.get("alt", "").strip(): self.imgs_alt += 1
        elif tag == "button": self._btn = True; self.buttons.append("")
        elif tag == "script":
            if "ld+json" in a.get("type", "").lower(): self.in_ld = True; self._ld = ""
            else: self.skip += 1
        elif tag == "style": self.skip += 1

    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        elif tag == "h1": self.in_h1 = False
        elif tag == "a" and self._a is not None: self.links.append((self._a, self._a_text.strip())); self._a = None
        elif tag == "button": self._btn = False
        elif tag == "script":
            if self.in_ld: self.in_ld = False; self.jsonld.append(self._ld)
            elif self.skip: self.skip -= 1
        elif tag == "style" and self.skip: self.skip -= 1

    def handle_data(self, data):
        if self.in_ld: self._ld += data; return
        if self.skip: return
        if self.in_title: self.title += data
        if self.in_h1 and self.h1: self.h1[-1] += data
        if self._a is not None: self._a_text += data
        if self._btn and self.buttons: self.buttons[-1] += data
        self.text.append(data)


def _flatten(node, out):
    if isinstance(node, list):
        for n in node: _flatten(n, out)
    elif isinstance(node, dict):
        out.append(node)
        for v in node.values():
            if isinstance(v, (list, dict)): _flatten(v, out)


def _types(node) -> List[str]:
    t = node.get("@type", [])
    return [t] if isinstance(t, str) else [x for x in t if isinstance(x, str)]


def _is_local(t: str) -> bool:
    return t in LOCAL_TYPES or t.endswith(("Business", "Contractor", "Clinic"))


def _robots_blocked(robots: str) -> List[str]:
    """AI crawlers that robots.txt blocks entirely (specific rule, or the * rule when no specific rule exists)."""
    groups: Dict[str, List[str]] = {}
    agents: List[str] = []
    last_was_agent = False
    for raw in robots.splitlines():
        line = raw.split("#")[0].strip()
        if ":" not in line: continue
        k, v = [x.strip() for x in line.split(":", 1)]
        k = k.lower()
        if k == "user-agent":
            if not last_was_agent: agents = []
            agents.append(v.lower()); groups.setdefault(v.lower(), []); last_was_agent = True
        else:
            last_was_agent = False
            if k == "disallow":
                for ag in agents: groups.setdefault(ag, []).append(v)
    blocked = []
    for bot in AI_BOTS:
        rules = groups.get(bot.lower(), groups.get("*", []) if bot.lower() not in groups else [])
        if "/" in rules: blocked.append(bot)
    return blocked


def _check(cid, label, weight, status, detail, fix=""):
    return {"id": cid, "label": label, "weight": weight, "status": status, "detail": detail, "fix": fix}


def audit(url: str, allow_private: bool = False) -> Dict[str, Any]:
    try:
        page = fetch(url, allow_private=allow_private)
    except FetchError as e:
        raise AuditError(str(e))
    if page["status"] >= 400:
        raise AuditError("The website returned an error (HTTP %d), so we couldn't read it." % page["status"])
    final = page["final_url"]
    root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(final))

    def aux(path):
        try:
            r = fetch(root + path, timeout=6, allow_private=allow_private)
            return r if r["status"] == 200 and r["text"].strip() else None
        except FetchError:
            return None

    llms, robots, sitemap = aux("/llms.txt"), aux("/robots.txt"), aux("/sitemap.xml")
    p = _Page()
    try: p.feed(page["text"])
    except Exception: pass

    nodes: List[dict] = []
    for blob in p.jsonld:
        try: _flatten(json.loads(blob), nodes)
        except ValueError: pass
    types = sorted({t for n in nodes for t in _types(n)})
    local = next((n for n in nodes if any(_is_local(t) for t in _types(n))), None)
    body_text = " ".join(" ".join(p.text).split())
    phone_link = next((h[4:] for h, _ in p.links if h.lower().startswith("tel:")), "")
    phone = phone_link or (local or {}).get("telephone", "") or (PHONE.search(body_text) or [""])[0]
    cta_hit = any(CTA.search(t) for _, t in p.links) or any(CTA.search(b) for b in p.buttons)
    title, desc = p.title.strip(), p.meta.get("description", "").strip()
    https = final.startswith("https://")
    blocked = _robots_blocked(robots["text"]) if robots else []
    alt_ratio = (p.imgs_alt / p.imgs) if p.imgs else 1.0
    words = len(body_text.split())

    C = []
    C.append(_check("https", "Secure connection (HTTPS)", 8, "pass" if https else "fail",
                    "Your site loads over HTTPS." if https else "Your site is not served over HTTPS.",
                    "" if https else "Enable HTTPS (most hosts offer a free certificate) so browsers and AI crawlers trust the site."))
    s = page["seconds"]
    C.append(_check("speed", "Page loads quickly", 6, "pass" if s < 2.5 else "warn" if s < 4.5 else "fail",
                    "Homepage HTML arrived in %.1f seconds." % s,
                    "" if s < 2.5 else "Compress images, remove unused plugins, and use caching or a CDN."))
    big = page["bytes"] > 1_000_000 or page["truncated"]
    C.append(_check("size", "Homepage is lightweight", 3, "warn" if big else "pass",
                    "Homepage HTML is %d KB." % (page["bytes"] // 1024), "Trim heavy inline scripts or embedded data." if big else ""))
    tl = len(title)
    C.append(_check("title", "Page title", 8, "pass" if 15 <= tl <= 65 else "warn" if tl else "fail",
                    ("Title is %d characters: \"%s\"" % (tl, title[:80])) if tl else "No <title> found.",
                    "" if 15 <= tl <= 65 else "Write a title of 15-65 characters naming your service and city."))
    dl = len(desc)
    C.append(_check("meta", "Meta description", 8, "pass" if 70 <= dl <= 170 else "warn" if dl else "fail",
                    ("Description is %d characters." % dl) if dl else "No meta description found.",
                    "" if 70 <= dl <= 170 else "Write a 70-170 character summary of what you offer and where."))
    C.append(_check("h1", "One clear main heading (H1)", 6, "pass" if len(p.h1) == 1 and p.h1[0].strip() else "warn",
                    "%d H1 heading(s) found." % len(p.h1), "" if len(p.h1) == 1 else "Use exactly one H1 that states what you do and where."))
    C.append(_check("mobile", "Mobile-friendly viewport", 6, "pass" if "viewport" in p.meta else "fail",
                    "Viewport tag present." if "viewport" in p.meta else "No viewport tag, so phones may show a shrunken desktop page.",
                    "" if "viewport" in p.meta else "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">."))
    if local:
        lt = next(t for t in _types(local) if _is_local(t))
        C.append(_check("schema", "Local business structured data (Schema.org)", 14, "pass", "Found structured data of type %s." % lt))
        has_addr, has_tel = bool(local.get("address")), bool(local.get("telephone"))
        C.append(_check("schema_detail", "Structured data includes phone and address", 6, "pass" if has_addr and has_tel else "warn",
                        "Phone: %s. Address: %s." % ("yes" if has_tel else "missing", "yes" if has_addr else "missing"),
                        "" if has_addr and has_tel else "Add telephone and address to your structured data."))
    else:
        C.append(_check("schema", "Local business structured data (Schema.org)", 14, "warn" if types else "fail",
                        ("Only generic types found: %s." % ", ".join(types)) if types else "No structured data found.",
                        "Add LocalBusiness JSON-LD so search engines and AI assistants can read your business facts reliably."))
        C.append(_check("schema_detail", "Structured data includes phone and address", 6, "fail", "No local business data to check.", "Included in the fix pack."))
    C.append(_check("bots", "AI assistants allowed to read your site", 10, "fail" if blocked else "pass",
                    ("robots.txt blocks: %s." % ", ".join(blocked)) if blocked else
                    ("robots.txt does not block major AI crawlers." if robots else "No robots.txt found, so nothing blocks AI crawlers."),
                    "Remove the blocking rules for these crawlers if you want those assistants to be able to cite you." if blocked else ""))
    C.append(_check("llms", "llms.txt summary file (emerging convention)", 4, "pass" if llms else "warn",
                    "llms.txt found." if llms else "No /llms.txt. This is a proposed, low-cost convention; support by AI products is not guaranteed.",
                    "" if llms else "Publish the generated llms.txt at your site root."))
    C.append(_check("sitemap", "XML sitemap", 6, "pass" if sitemap else "warn", "sitemap.xml found." if sitemap else "No /sitemap.xml found.",
                    "" if sitemap else "Publish a sitemap so crawlers discover all your pages."))
    C.append(_check("phone", "Phone number visible", 6, "pass" if phone else "fail",
                    ("Found: %s" % phone[:30]) if phone else "No phone number detected on the homepage.",
                    "" if phone else "Show a clickable phone number (tel: link) near the top."))
    C.append(_check("cta", "Clear call to action (book / quote / call)", 6, "pass" if cta_hit else "fail",
                    "Found a booking or contact call to action." if cta_hit else "No clear booking, quote or call button detected.",
                    "" if cta_hit else "Add a prominent button such as \"Book now\" or \"Get a free quote\"."))
    C.append(_check("alt", "Images have descriptive alt text", 4, "pass" if alt_ratio >= 0.8 else "warn",
                    "%d of %d images have alt text." % (p.imgs_alt, p.imgs), "" if alt_ratio >= 0.8 else "Describe each image in its alt attribute."))
    C.append(_check("content", "Enough readable text on the homepage", 4, "pass" if words >= 150 else "warn",
                    "About %d words of readable text." % words, "" if words >= 150 else "Add a short explanation of your services, area and contact details."))

    got = sum(c["weight"] * {"pass": 1, "warn": 0.5, "fail": 0}[c["status"]] for c in C)
    score = round(100 * got / sum(c["weight"] for c in C))
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
    name = p.meta.get("og:site_name") or (local or {}).get("name") or re.split(r"\s[|\u2013\u2014:\u00b7-]\s", title)[0].strip() or urllib.parse.urlsplit(final).hostname
    internal = []
    for h, t in p.links:
        u = urllib.parse.urljoin(final, h)
        if urllib.parse.urlsplit(u).netloc == urllib.parse.urlsplit(final).netloc and t and not h.startswith(("#", "tel:", "mailto:")) and u not in [x[1] for x in internal]:
            internal.append((t[:60], u.split("#")[0]))
    return {"url": url, "final_url": final, "root": root, "score": score, "grade": grade, "checks": C,
            "blocked_bots": blocked, "existing_llms": llms["text"] if llms else "", "robots_text": robots["text"] if robots else "",
            "profile": {"name": name[:80], "title": title, "description": desc, "phone": phone, "address": (local or {}).get("address"),
                        "types": types, "local_type": next((t for t in _types(local) if _is_local(t)), None) if local else None,
                        "links": internal[:10], "lang": p.lang, "h1": p.h1[:1], "excerpt": body_text[:900]},
            "fetched_at": int(time.time())}
