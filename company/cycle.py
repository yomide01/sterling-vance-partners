"""One daily run of the company (GitHub Actions calls this). Run locally: python -m company.cycle"""
import time

from . import config, publisher
from .agents import ceo, distribution, guardian, quality, reporter, writer


def run() -> dict:
    existing = set(publisher.all_guides())
    plan = ceo.plan(existing)
    published, rejected = [], []
    for t in plan["topics"]:
        guardian.allow("publish_guide")
        g = writer.draft(t)
        if not g:
            rejected.append({"slug": t["slug"], "why": ["writer unavailable (no AI key or API error)"]})
            continue
        ok, why = quality.check(g)
        if ok:
            publisher.save_guide(t["slug"], g)
            published.append(t["slug"])
        else:
            rejected.append({"slug": t["slug"], "why": why})
            d = config.ROOT / "data" / "rejected"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{t['slug']}.json").write_text(__import__("json").dumps(g, indent=2, ensure_ascii=False))
    total = publisher.rebuild_indexes()
    announced = distribution.announce(published, publisher.all_guides()) if published else {}
    report = {"date": time.strftime("%Y-%m-%d", time.gmtime()), "published": published, "rejected": rejected,
              "total_guides": total, "distribution": announced, "weekly_review": plan.get("review", ""), "money": plan["money"], "ceo_note": plan["note"]}
    reporter.save(report)
    reporter.telegram(reporter.summary(report))
    return report


if __name__ == "__main__":
    print(run())
