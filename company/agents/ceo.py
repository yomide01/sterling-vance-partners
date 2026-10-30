"""CEO agent: sets the day's plan from real numbers and enforces the company's limits. Staff = the other agents."""
from .. import config, payments
from . import research


def plan(existing_slugs: set) -> dict:
    money = None
    if payments.enabled():
        try:
            money = payments.revenue_last_days(30)
        except Exception:
            money = None
    n = config.MAX_GUIDES_PER_DAY  # one place to scale content output as the company earns
    topics = research.next_topics(existing_slugs, n)
    note = ("Plan: publish %d guide(s). " % len(topics)) + ("No new topics left." if not topics else "Topics: " + "; ".join(t["slug"] for t in topics))
    if money and money["sales"] == 0:
        note += " No sales yet: acquisition (guides + free checker) is the focus; price and product stay unchanged until there is data."
    return {"topics": topics, "money": money, "note": note}
