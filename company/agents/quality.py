"""Quality agent: nothing is published unless it passes. Stops thin, spammy or invented content,
but allows honest disclaimers such as 'nobody can guarantee results'."""
import re
from typing import Tuple

HARD = re.compile(r"(studies show|research shows|according to (a |an |the )?(recent |new |latest )?(study|survey|report|poll)|"
                  r"#1 ranked|case study|our clients?|testimonial|\b\d{2,3}\s?%|[$\u20a6\u00a3\u20ac]\s?\d)", re.I)
PROMISE = re.compile(r"(guarantee[sd]?|top of google|number one (spot|rank|result)|\brank(ed|s|ing)? (first|#1|number one)|\bfirst[- ]place (rank|spot|result|position))", re.I)
NEGATION = re.compile(r"(no |not |n't |never |nobody |no one |cannot |can't |without |neither |nor |isn't |aren't |rather than )", re.I)


def claims(text: str) -> list:
    found = [m.group(0) for m in HARD.finditer(text)]
    for m in PROMISE.finditer(text):
        before = re.split(r"[.!?\n]", text[max(0, m.start() - 60):m.start()])[-1]  # same sentence only
        if not NEGATION.search(before):
            found.append(text[max(0, m.start() - 25):m.end() + 15].replace("\n", " "))
    return found


def check(g: dict) -> Tuple[bool, list]:
    why = []
    secs = g.get("sections") or []
    text = " ".join(str(s.get("body", "")) for s in secs) + " " + " ".join(str(f.get("a", "")) for f in g.get("faq", []))
    if not g.get("title") or not g.get("description"):
        why.append("missing title/description")
    if len(secs) < 4:
        why.append("fewer than 4 sections")
    if len(" ".join(str(s.get("body", "")) for s in secs).split()) < 650:
        why.append("under 650 words")
    bad = claims(text + " " + str(g.get("title", "")))
    if bad:
        why.append("unsupported claims: " + " | ".join(bad[:3]))
    if len(set(s.get("h2", "") for s in secs)) < len(secs):
        why.append("duplicate headings")
    if not (50 <= len(str(g.get("description", ""))) <= 175):
        why.append("description length (%d)" % len(str(g.get("description", ""))))
    return (not why), why
