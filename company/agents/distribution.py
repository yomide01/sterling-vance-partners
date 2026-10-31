"""Distribution agent: tells the world a new guide exists, using only our OWN channels and open, official APIs.
(No messaging of strangers, no comment-dropping, no fake accounts.)"""
import hashlib
import json
import time
import urllib.request

from .. import config
from . import guardian


def indexnow_key() -> str:
    return config.env("INDEXNOW_KEY") or hashlib.sha256(("indexnow:" + config.BASE_URL).encode()).hexdigest()[:32]


def ping_indexnow(urls: list) -> bool:
    """Free, official protocol (Bing, Yandex and others): tells search engines about new pages immediately."""
    if not urls or config.BASE_URL.startswith("http://localhost"):
        return False
    guardian.allow("notify_search_engines")
    host = config.BASE_URL.split("//", 1)[1]
    body = json.dumps({"host": host, "key": indexnow_key(), "keyLocation": f"{config.BASE_URL}/{indexnow_key()}.txt", "urlList": urls[:50]}).encode()
    try:
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST", headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=20).status in (200, 202)
    except Exception:
        return False


def _post_json(url, body, headers=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read() or b"{}")


def post_bluesky(title: str, description: str, url: str) -> bool:
    """Posts to OUR OWN Bluesky account (free official API; needs BLUESKY_HANDLE + BLUESKY_APP_PASSWORD)."""
    handle, pw = config.env("BLUESKY_HANDLE"), config.env("BLUESKY_APP_PASSWORD")
    if not (handle and pw):
        return False
    guardian.allow("post_to_own_channel")
    try:
        sess = _post_json("https://bsky.social/xrpc/com.atproto.server.createSession", {"identifier": handle, "password": pw})
        text = (title[:150] + "\n\n" + description[:100].rstrip() + "\n\n").replace("\n\n\n", "\n\n")
        start = len(text.encode())
        text += url
        record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "facets": [{"index": {"byteStart": start, "byteEnd": start + len(url.encode())},
                              "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]}]}
        _post_json("https://bsky.social/xrpc/com.atproto.repo.createRecord",
                   {"repo": sess["did"], "collection": "app.bsky.feed.post", "record": record}, {"Authorization": "Bearer " + sess["accessJwt"]})
        return True
    except Exception:
        return False


def post_telegram_channel(title: str, url: str) -> bool:
    ch = config.env("TELEGRAM_CHANNEL_ID")
    if not (config.TELEGRAM_BOT_TOKEN and ch):
        return False
    guardian.allow("post_to_own_channel")
    try:
        _post_json(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage", {"chat_id": ch, "text": f"{title}\n{url}"})
        return True
    except Exception:
        return False


def announce(published: list, guides: dict) -> dict:
    urls = [f"{config.BASE_URL}/guides/{s}.html" for s in published]
    out = {"indexnow": ping_indexnow(urls + [config.BASE_URL + "/guides/"]) if urls else False, "bluesky": 0, "telegram_channel": 0}
    for s in published[: config.MAX_GUIDES_PER_DAY]:
        g, u = guides[s], f"{config.BASE_URL}/guides/{s}.html"
        out["bluesky"] += int(post_bluesky(g["title"], g["description"], u))
        out["telegram_channel"] += int(post_telegram_channel(g["title"], u))
    return out
