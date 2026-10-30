"""Optional Gemini helper. The company still runs without a key; it just skips AI-written parts."""
import json
import time
import urllib.request

from . import config


def generate(prompt: str, as_json: bool = False, temperature: float = 0.4):
    """Returns text (or parsed JSON when as_json=True), or None if unavailable. Key goes in a header, never a URL."""
    if not config.GEMINI_API_KEY:
        return None
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature}}
    if as_json:
        body["generationConfig"]["response_mime_type"] = "application/json"
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text) if as_json else text
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None
