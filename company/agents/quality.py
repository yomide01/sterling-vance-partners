"""Quality agent: nothing is published unless it passes. Stops thin, spammy or invented content."""
import re
from typing import Tuple

BAD_PHRASES = re.compile(r"(studies show|research shows|according to (a )?(recent )?(study|survey|report)|guarantee[sd]?|#1 ranked|first place|top of google|"
                         r"case study|our client|testimonial|\b\d{2,3}\s?%|\$\s?\d)", re.I)


def check(g: dict) -> Tuple[bool, list]:
    why = []
    secs = g.get("sections") or []
    text = " ".join(str(s.get("body", "")) for s in secs)
    if not g.get("title") or not g.get("description"):
        why.append("missing title/description")
    if len(secs) < 4:
        why.append("fewer than 4 sections")
    if len(text.split()) < 650:
        why.append("under 650 words")
    if BAD_PHRASES.search(text + " " + str(g.get("title", ""))):
        why.append("contains statistics, guarantees or testimonial-style claims we cannot back up")
    if len(set(s.get("h2", "") for s in secs)) < len(secs):
        why.append("duplicate headings")
    if not (50 <= len(str(g.get("description", ""))) <= 175):
        why.append("description length")
    return (not why), why
