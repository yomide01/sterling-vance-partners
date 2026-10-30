"""Builds the paid fix pack from the audited site's real data. Fields we could not find are left as clearly
marked blanks for the owner; we never invent addresses, hours, reviews or ratings."""
import json
import re
from typing import Any, Dict

from . import llm


def build_jsonld(a: Dict[str, Any]) -> str:
    p = a["profile"]
    data: Dict[str, Any] = {"@context": "https://schema.org", "@type": p["local_type"] or "LocalBusiness",
                            "name": p["name"], "url": a["root"] + "/"}
    if p["description"]: data["description"] = p["description"]
    data["telephone"] = p["phone"] or "FILL IN: +country code and number"
    data["address"] = p["address"] or {"@type": "PostalAddress", "streetAddress": "FILL IN", "addressLocality": "FILL IN",
                                       "addressRegion": "FILL IN", "postalCode": "FILL IN", "addressCountry": "FILL IN"}
    data["openingHours"] = "FILL IN, e.g. Mo-Fr 09:00-17:00"
    return '<script type="application/ld+json">\n' + json.dumps(data, indent=2, ensure_ascii=False) + "\n</script>"


def build_llms_txt(a: Dict[str, Any]) -> str:
    p = a["profile"]
    lines = ["# " + p["name"], ""]
    if p["description"] or p["title"]:
        lines += ["> " + (p["description"] or p["title"]), ""]
    if p["links"]:
        lines.append("## Key pages")
        lines += ["- [%s](%s)" % (t, u) for t, u in p["links"]]
        lines.append("")
    lines += ["## Contact", "- Website: " + a["root"] + "/"]
    if p["phone"]: lines.append("- Phone: " + p["phone"])
    return "\n".join(lines) + "\n"


def build_robots_fix(a: Dict[str, Any]) -> str:
    if not a["blocked_bots"]:
        return "# Your robots.txt does not block the major AI crawlers. No change needed.\n"
    out = ["# Add these groups to robots.txt to let these assistants read (and cite) your public pages.",
           "# Only do this if you are comfortable with it; blocking is your right."]
    for b in a["blocked_bots"]:
        out += ["User-agent: " + b, "Allow: /", ""]
    out.append("# Also remove any 'Disallow: /' rule under a matching or wildcard (*) group that blocks these bots.")
    return "\n".join(out) + "\n"


def build_meta(a: Dict[str, Any]) -> str:
    p = a["profile"]
    prompt = ("You write website metadata. Using ONLY the facts below, write one page title (max 60 characters) and one "
              "meta description (110-160 characters). Do not invent services, locations, awards or numbers. "
              "Return JSON {\"title\":\"...\",\"description\":\"...\"}.\nBusiness: %s\nCurrent title: %s\nCurrent description: %s\n"
              "Homepage text excerpt: %s" % (p["name"], p["title"], p["description"], p["excerpt"]))
    r = llm.generate(prompt, as_json=True)
    if isinstance(r, dict) and r.get("title") and r.get("description"):
        t, d = str(r["title"])[:70], str(r["description"])[:170]
        return "<title>%s</title>\n<meta name=\"description\" content=\"%s\">\n" % (t, d.replace('"', "&quot;"))
    return ("<title>%s | FILL IN: your main service and city</title>\n<meta name=\"description\" content=\"FILL IN: 110-160 characters "
            "saying what you offer, where, and how to book.\">\n" % p["name"])


GUIDE = """HOW TO INSTALL (about 20 minutes)
1. WordPress: install a free 'header and footer code' plugin, paste the structured-data block (file 1) into the header,
   and the title/description (file 4) into your SEO plugin's fields.
2. Wix / Squarespace / Shopify: use Settings > Custom code (or Code Injection) for file 1. Upload llms.txt and robots
   changes where your platform allows root files; if it does not, skip those two and do the rest.
3. Replace every 'FILL IN' with your real details. Never publish placeholder text.
4. Test: Google Rich Results Test (search.google.com/test/rich-results) accepts the structured-data block.
5. Re-open this page anytime: your score is re-measured live from your site.

NOTE: llms.txt is a proposed convention. We cannot promise any AI product reads it. Structured data and open
crawler access are the parts with the clearest benefit.
"""


def build_pack(a: Dict[str, Any]) -> Dict[str, str]:
    return {"1-structured-data.html": build_jsonld(a), "2-llms.txt": build_llms_txt(a), "3-robots-fix.txt": build_robots_fix(a),
            "4-title-and-description.html": build_meta(a), "5-install-guide.txt": GUIDE}
