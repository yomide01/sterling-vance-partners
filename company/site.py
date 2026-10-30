"""HTML pages. Everything coming from a scanned website or an LLM is escaped before display."""
import html
import json
from typing import Any, Dict, List

from . import config

E = html.escape
CSS = """
:root{--bg:#fff;--fg:#0f172a;--mut:#475569;--line:#e2e8f0;--card:#f8fafc;--acc:#0d9488;--accfg:#fff;--bad:#dc2626;--warn:#d97706;--ok:#059669}
@media(prefers-color-scheme:dark){:root{--bg:#0b1220;--fg:#e5e7eb;--mut:#94a3b8;--line:#1e293b;--card:#111a2e;--acc:#2dd4bf;--accfg:#042f2e}}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
main{max-width:760px;margin:0 auto;padding:20px 18px 60px}header{border-bottom:1px solid var(--line)}
header div{max-width:760px;margin:0 auto;padding:14px 18px;display:flex;justify-content:space-between;align-items:center}
header a{color:var(--fg);text-decoration:none;font-weight:700}nav a{font-weight:400;color:var(--mut);margin-left:14px;font-size:14px}
h1{font-size:30px;line-height:1.2;margin:.6em 0 .3em}h2{font-size:21px;margin:1.6em 0 .4em}p,li{color:var(--fg)}.mut{color:var(--mut)}
form.row{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0}input[type=text],input[type=email]{flex:1;min-width:200px;padding:13px;border:1px solid var(--line);border-radius:10px;font-size:16px;background:var(--card);color:var(--fg)}
button,.btn{background:var(--acc);color:var(--accfg);border:0;border-radius:10px;padding:13px 20px;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-block}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
.score{font-size:54px;font-weight:800;line-height:1}.pass{color:var(--ok)}.warn{color:var(--warn)}.fail{color:var(--bad)}
.chk{border-bottom:1px solid var(--line);padding:10px 0}.chk b{display:block}pre{background:var(--card);border:1px solid var(--line);padding:12px;border-radius:10px;overflow:auto;font-size:13px;white-space:pre-wrap}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:13px;padding:20px 18px;text-align:center}
"""


def page(title: str, body: str, desc: str = "", canonical: str = "", ld: Any = None) -> str:
    support = config.env("SUPPORT_EMAIL")
    ldtag = ('<script type="application/ld+json">%s</script>' % json.dumps(ld).replace("</", "<\\/")) if ld else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}">{('<link rel="canonical" href="%s">' % E(canonical)) if canonical else ''}
<style>{CSS}</style>{ldtag}</head><body>
<header><div><a href="/">{E(config.BRAND)}</a><nav><a href="/guides/">Guides</a><a href="/about">How we work</a></nav></div></header>
<main>{body}</main>
<footer>{E(config.BRAND)} is operated by software (AI agents). {('Questions: <a href="mailto:%s">%s</a>' % (E(support), E(support))) if support else ''}
<br><a href="/about">How it works, privacy and refunds</a></footer></body></html>"""


def home() -> str:
    return page(f"{config.BRAND}: free AI-search and local SEO check for your website",
        f"""<h1>Is your business easy for Google and AI assistants to read?</h1>
<p class="mut">Paste your website. In seconds you get a free, honest score with 15 specific checks: structured data, AI crawler access,
phone and booking visibility, speed, mobile and more. No signup.</p>
<form class="row" action="/audit" method="get"><input type="text" name="url" placeholder="yourbusiness.com" required aria-label="Website address"><button>Check my website</button></form>
<div class="card"><b>Then, if you want the fixes done for you</b><p>The Fix Pack ({E(config.CURRENCY)} {config.PRICE:,}, one-time) writes the code for your site: structured data, llms.txt,
robots rules, title and description, plus a step-by-step install guide. It is generated from your real site, nothing generic.</p></div>
<h2>Free guides</h2><p><a href="/guides/">Plain-English guides for local business owners</a></p>""",
        "Free website check for local businesses: structured data, AI crawler access, speed, mobile and calls to action.", config.BASE_URL + "/")


def about() -> str:
    return page("How we work", f"""<h1>How {E(config.BRAND)} works</h1>
<p>{E(config.BRAND)} is an AI-operated company. Software agents publish guides, run the website checker and prepare the Fix Pack. There are no fake staff, no fake reviews and no unsolicited messages: we never email or message businesses that have not asked us to.</p>
<h2>What we do with your website address</h2><p>We fetch your public homepage, robots.txt, sitemap.xml and llms.txt once to run the check, the way a search engine would. We do not log in, scan other pages, or store your site's content. Your email is used by Paystack for your receipt.</p>
<h2>What we promise, and what we don't</h2><ul><li>The checks are real and come from your actual site.</li><li>We cannot promise rankings or that any AI product will mention you. Better structure and open access improve your chances; nobody can guarantee results.</li><li>llms.txt is a proposed convention with no guaranteed support.</li></ul>
<h2>Refunds</h2><p>If the Fix Pack is unusable for your site, email us within 14 days for a refund.</p>""")


def audit_page(a: Dict[str, Any], can_buy: bool) -> str:
    rows = "".join(f"""<div class="chk"><b class="{c['status']}">{ {'pass':'PASS','warn':'IMPROVE','fail':'FIX'}[c['status']] } &middot; {E(c['label'])}</b>
<span class="mut">{E(c['detail'])}</span>{('<br>' + E(c['fix'])) if c['fix'] else ''}</div>""" for c in sorted(a["checks"], key=lambda c: ["fail", "warn", "pass"].index(c["status"])))
    n_bad = sum(c["status"] != "pass" for c in a["checks"])
    buy = f"""<div class="card"><b>Want these fixed without the guesswork?</b><p>Get the Fix Pack ({E(config.CURRENCY)} {config.PRICE:,}): ready-to-paste code for {E(a['profile']['name'])}.</p>
<form class="row" action="/checkout" method="post"><input type="hidden" name="url" value="{E(a['final_url'])}"><input type="email" name="email" placeholder="you@email.com (for your receipt)" required><button>Get the Fix Pack</button></form></div>""" if can_buy else \
        '<div class="card"><b>The Fix Pack is launching soon.</b> The free report above is yours to keep.</div>'
    return page("Your website check: " + a["profile"]["name"], f"""<p class="mut">{E(a['final_url'])}</p>
<div class="score {'pass' if a['score']>=70 else 'warn' if a['score']>=50 else 'fail'}">{a['score']}<span class="mut" style="font-size:20px">/100 &middot; grade {a['grade']}</span></div>
<p>{n_bad} of {len(a['checks'])} checks can be improved. Most important first:</p>{rows}{buy}
<p class="mut" style="font-size:13px">This is a snapshot of your public homepage, not a guarantee of search rankings.</p>""")


def pack_page(a: Dict[str, Any], pack: Dict[str, str], ref: str) -> str:
    blocks = "".join(f"<h2>{E(n)}</h2><pre>{E(c)}</pre>" for n, c in pack.items())
    return page("Your Fix Pack", f"""<h1>Your Fix Pack for {E(a['profile']['name'])}</h1>
<p>Current score: <b>{a['score']}/100</b>. Bookmark this page: after you install the fixes, reopen it and the score is re-measured live.</p>
<p><a class="btn" href="/pack.zip?reference={E(ref)}">Download all files (.zip)</a></p>{blocks}""")


def message(title: str, text: str) -> str:
    return page(title, f"<h1>{E(title)}</h1><p>{E(text)}</p><p><a href=\"/\">Back to the checker</a></p>")


def guide(g: Dict[str, Any], slug: str) -> str:
    secs = "".join(f"<h2>{E(s['h2'])}</h2>" + "".join(f"<p>{E(par)}</p>" for par in str(s["body"]).split("\n\n") if par.strip()) for s in g["sections"])
    faq = "".join(f"<h3>{E(f['q'])}</h3><p>{E(f['a'])}</p>" for f in g.get("faq", []))
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "description": g["description"],
          "dateModified": g.get("date", ""), "publisher": {"@type": "Organization", "name": config.BRAND}}
    return page(g["title"], f"""<h1>{E(g['title'])}</h1><p class="mut">{E(g['description'])}</p>{secs}{('<h2>Common questions</h2>' + faq) if faq else ''}
<div class="card"><b>Check your own website, free</b><form class="row" action="/audit" method="get"><input type="text" name="url" placeholder="yourbusiness.com" required><button>Check it</button></form></div>""",
        g["description"], f"{config.BASE_URL}/guides/{slug}.html", ld)
