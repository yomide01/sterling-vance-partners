"""Optional Gemini helper (Gemini Developer API, free tier). The company still runs without a key; it just skips AI-written parts."""
import json
import time
import urllib.error
import urllib.request

from . import config

FALLBACK_MODELS = ["gemini-3.8-flash"]  # used if the configured model gets retired (HTTP 404)


def generate(prompt: str, as_json: bool = False, temperature: float = 0.4):
    """Returns text (or parsed JSON when as_json=True), or None if unavailable. The key goes in a header, never a URL."""
    if not config.GEMINI_API_KEY:
        return None
    cfg = {"temperature": temperature}
    if as_json:
        cfg["responseMimeType"] = "application/json"
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg}).encode()
    models = [config.GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != config.GEMINI_MODEL]
    for attempt in range(3):
        for model in models:
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", data=data, method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY})
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    text = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text) if as_json else text
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue  # model retired: try the next one
                break  # rate limit / server error: back off and retry
            except Exception:
                break
        time.sleep(4 * (attempt + 1))
    return None
