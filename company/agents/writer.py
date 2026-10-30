"""Writer agent: drafts a genuinely useful guide with Gemini, under strict rules; the Quality agent has the final say."""
import time

from .. import llm

RULES = """You write practical guides for owners of small local businesses. Plain English, no hype.
HARD RULES: do not state any statistic, percentage, price, ranking promise or study. Do not invent customers, case studies,
testimonials or quotes. Do not claim any AI product definitely uses a specific signal; say 'can help' or 'is worth doing'.
llms.txt is a proposed convention with no guaranteed support: say so if you mention it. Be concrete and actionable."""


def draft(topic: dict):
    prompt = f"""{RULES}
Write a guide titled: "{topic['title']}" for owners of {topic['niche']}.
Return JSON: {{"title": str, "description": str (60-160 chars), "sections": [{{"h2": str, "body": str (2-4 paragraphs separated by blank lines)}}] (5-7 sections, total 800-1200 words),
"faq": [{{"q": str, "a": str}}] (3 items)}}"""
    g = llm.generate(prompt, as_json=True)
    if isinstance(g, dict):
        g["date"] = time.strftime("%Y-%m-%d", time.gmtime())
    return g if isinstance(g, dict) else None
