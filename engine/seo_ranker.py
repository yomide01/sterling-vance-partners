"""
Sterling & Vance Partners — Google #1 Search Authority & Sitemap Engine
Generates high-authority Schema.org JSON-LD, XML Sitemaps, and IndexNow payloads
so the public customer portal ranks at the top of search results and serves 2,000+ daily users.
"""

import os
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
os.makedirs(PUBLIC_DIR, exist_ok=True)


def rebuild_seo_sitemap(prospects: list, base_domain: str = "https://sterlingvance.com"):
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [
        f"""  <url>
    <loc>{base_domain}/</loc>
    <lastmod>{now_date}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>"""
    ]
    for p in prospects[:50]:
        slug = p.get("slug", "")
        if slug:
            urls.append(
                f"""  <url>
    <loc>{base_domain}/client-build/{slug}.html</loc>
    <lastmod>{now_date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>"""
            )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    with open(os.path.join(PUBLIC_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)

    robots = f"User-agent: *\nAllow: /\nDisallow: /founder-command-vault\nDisallow: /api/founder-\nSitemap: {base_domain}/sitemap.xml\n"
    with open(os.path.join(PUBLIC_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)
