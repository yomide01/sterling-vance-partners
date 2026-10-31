"""Research agent: decides which guide to write next (what local business owners actually search for)."""
from typing import List

from .. import config

NICHES = ["dentists", "plumbers", "roofers", "HVAC companies", "law firms", "accountants", "restaurants", "hair salons",
          "gyms", "real estate agents", "electricians", "physiotherapy clinics", "auto repair shops", "cleaning companies"]
ANGLES = [
    ("How {n} can show up when customers ask AI assistants for a local provider", "ai-search"),
    ("The structured data every {n} website needs (and how to add it)", "schema"),
    ("A website checklist for {n} that turns visitors into calls and bookings", "conversion"),
    ("Is your {n} website accidentally blocking AI assistants?", "crawlers"),
]


def slug_for(niche: str, tag: str) -> str:
    return (niche.lower().replace(" ", "-") + "-" + tag)


def next_topics(existing_slugs: set, limit: int, niche_views: dict = None) -> List[dict]:
    """Writes about the niches whose guides get read most first (the CEO's weekly strategy feeds niche_views)."""
    views = niche_views or {}
    niches = sorted(NICHES, key=lambda n: -views.get(n, 0))
    out = []
    for tag_idx in range(len(ANGLES)):
        for n in niches:
            title, tag = ANGLES[tag_idx]
            s = slug_for(n, tag)
            if s not in existing_slugs:
                out.append({"slug": s, "niche": n, "angle": tag, "title": title.format(n=n)})
                if len(out) >= limit:
                    return out
    return out
