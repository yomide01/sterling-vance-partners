# Sterling & Vance: an AI-run company

A small online company that is operated by software agents and earns from real customers who find it on their own.

**The product.** A free website checker for local businesses (15 real checks: structured data, AI-crawler access, speed, mobile,
phone/booking visibility). Owners who want the fixes pay once for a **Fix Pack** generated from their actual site.

**How customers arrive (no outreach).** The Writer agent publishes helpful guides every day; they rank in search and get read by AI
assistants. Each guide embeds the free checker. Nobody is ever emailed or messaged unless they came to us.

## The team (each is a real module)
| Agent | Job |
|---|---|
| CEO (`agents/ceo.py`) | Reads real sales from Paystack, sets the daily plan, enforces limits |
| Research (`agents/research.py`) | Chooses which guide to write next |
| Writer (`agents/writer.py`) | Drafts the guide with Gemini under strict rules |
| Quality (`agents/quality.py`) | Rejects thin, hyped or unsupported content |
| Guardian (`agents/guardian.py`) | Blocks forbidden actions: spam, fake reviews, invented stats, spending |
| Publisher (`publisher.py`) | Publishes pages, sitemap, robots.txt, llms.txt |
| Reporter (`agents/reporter.py`) | Sends you the daily summary (Telegram) |
| Auditor + Fixer (`auditor.py`, `fixes.py`) | The product itself, run on demand for customers |

Setup is in **SETUP.md**. Run the tests with `python -m unittest discover -s tests`.
