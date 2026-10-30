"""Guardian agent: the company's conscience. Every action any agent wants to take is checked here first.
The code base contains no email-sending, scraping-for-contacts or review-posting capability at all;
this list makes the rule explicit and a test makes sure it stays that way."""

FORBIDDEN = {
    "send_unsolicited_message": "We only talk to people who came to us.",
    "scrape_contact_details": "We do not collect people's emails, phones or social handles.",
    "post_fake_review": "No fake reviews or testimonials, ever.",
    "invent_statistic": "No made-up numbers or case studies.",
    "spend_money": "The company runs on free tiers only.",
    "evade_platform_rules": "No bypassing a platform's rules or blocks.",
}


class Violation(Exception):
    pass


def allow(action: str) -> bool:
    """Raise if an agent tries something forbidden; return True otherwise."""
    if action in FORBIDDEN:
        raise Violation(f"{action}: {FORBIDDEN[action]}")
    return True
