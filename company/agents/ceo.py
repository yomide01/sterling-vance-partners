"""CEO agent: reads real numbers, decides what the company does next, and reviews strategy weekly."""
import json
import time
import urllib.request

from .. import config, payments
from . import research

STRATEGY = config.ROOT / "data" / "strategy.json"
HISTORY = config.ROOT / "data" / "metrics.json"


def fetch_stats():
    """Pull live counters from our own website (needs STATS_TOKEN). 60s timeout covers a cold start on the free host."""
    if not config.STATS_TOKEN or config.BASE_URL.startswith("http://localhost"):
        return None
    try:
        req = urllib.request.Request(config.BASE_URL + "/stats", headers={"Authorization": "Bearer " + config.STATS_TOKEN})
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception:
        return None


def niche_views(guide_views: dict) -> dict:
    out = {}
    for n in research.NICHES:
        prefix = n.lower().replace(" ", "-") + "-"
        out[n] = sum(v for s, v in guide_views.items() if s.startswith(prefix))
    return out


def record(stats) -> None:
    if not stats:
        return
    hist = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    hist.append({"date": time.strftime("%Y-%m-%d", time.gmtime()), **{k: stats[k] for k in ("boot_id", "audits", "checkout_started", "guide_views")}})
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(hist[-90:], indent=1))


def weekly_review(stats, money) -> str:
    """Mondays: a short written review the founder can read. Uses Gemini if available, otherwise plain facts."""
    from .. import llm
    facts = {"stats": {k: stats[k] for k in ("audits", "checkout_started", "guide_views")} if stats else None, "money": money,
             "niche_views": niche_views(stats["guide_views"]) if stats else None}
    text = llm.generate("You are the CEO of a tiny AI-run company that sells a website-audit Fix Pack to local businesses. Using ONLY these "
                        "facts, write a 5-line weekly review: what is working, what is not, and the one thing to do next week. "
                        "Do not invent numbers.\n" + json.dumps(facts)) or ("Weekly facts: " + json.dumps(facts))
    (config.REPORTS / "weekly_review.md").write_text(text)
    return text


def plan(existing_slugs: set) -> dict:
    money = None
    if payments.enabled():
        try:
            money = payments.revenue_last_days(30)
        except Exception:
            money = None
    stats = fetch_stats()
    record(stats)
    views = niche_views(stats["guide_views"]) if stats else {}
    if views:
        STRATEGY.write_text(json.dumps({"updated": time.strftime("%Y-%m-%d", time.gmtime()), "niche_views": views}, indent=1))
    elif STRATEGY.exists():
        views = json.loads(STRATEGY.read_text()).get("niche_views", {})
    topics = research.next_topics(existing_slugs, config.MAX_GUIDES_PER_DAY, views)
    note = ("Plan: publish %d guide(s). " % len(topics)) + ("No new topics left." if not topics else "Topics: " + "; ".join(t["slug"] for t in topics))
    if stats:
        note += " Live: %d audits, %d checkouts started since last restart." % (stats["audits"], stats["checkout_started"])
    if any(views.values()):
        top = max(views, key=views.get)
        note += " Most-read niche so far: %s." % top
    if money and money["sales"] == 0:
        note += " No sales yet: acquisition is the focus; price and product stay unchanged until there is data."
    review = weekly_review(stats, money) if time.gmtime().tm_wday == 0 else ""
    return {"topics": topics, "money": money, "note": note, "stats": stats, "review": review}
