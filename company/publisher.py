"""Publishes guides and rebuilds the company's own discovery files (guide index, sitemap, robots.txt, llms.txt)."""
import json
import time
from pathlib import Path

from . import config, site

G = config.PUBLIC / "guides"


def save_guide(slug: str, g: dict) -> None:
    G.mkdir(parents=True, exist_ok=True)
    (G / f"{slug}.json").write_text(json.dumps(g, indent=2, ensure_ascii=False))
    (G / f"{slug}.html").write_text(site.guide(g, slug))


def all_guides() -> dict:
    return {p.stem: json.loads(p.read_text()) for p in sorted(G.glob("*.json"))} if G.exists() else {}


def rebuild_indexes() -> int:
    guides = all_guides()
    items = "".join(f'<li><a href="/guides/{s}.html">{site.E(g["title"])}</a></li>' for s, g in sorted(guides.items(), key=lambda kv: kv[1].get("date", ""), reverse=True))
    (G / "index.html").write_text(site.page(f"Guides for local business owners | {config.BRAND}",
        f"<h1>Guides for local business owners</h1><ul>{items or '<li>First guides are on the way.</li>'}</ul>",
        "Practical, plain-English guides on getting found by Google and AI assistants.", config.BASE_URL + "/guides/"))
    today = time.strftime("%Y-%m-%d", time.gmtime())
    urls = ["/", "/about", "/guides/"] + [f"/guides/{s}.html" for s in guides]
    (config.PUBLIC / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{config.BASE_URL}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    (config.PUBLIC / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /thanks\nDisallow: /pack.zip\n\nSitemap: {config.BASE_URL}/sitemap.xml\n")
    top = "\n".join(f"- [{g['title']}]({config.BASE_URL}/guides/{s}.html): {g['description']}" for s, g in list(guides.items())[:30])
    (config.PUBLIC / "llms.txt").write_text(f"# {config.BRAND}\n\n> Free website check for local businesses (AI-search readiness and local SEO basics), "
        f"plus practical guides. Operated by AI agents.\n\n## Tools\n- [Free website check]({config.BASE_URL}/)\n\n## Guides\n{top}\n")
    return len(guides)
