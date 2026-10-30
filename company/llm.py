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
    # Keys starting with "AQ." are Vertex AI Express keys (different host); "AIza..." keys use the Gemini Developer API.
    if config.GEMINI_API_KEY.startswith("AQ."):
        url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{config.GEMINI_MODEL}:generateContent"
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    if as_json:
        body["generationConfig"] = {"temperature": temperature, "responseMimeType": "application/json"}
        body["generationConfig"].pop("response_mime_type", None)
    data = json.dumps(body).encode()
    attempts = [{"x-goog-api-key": config.GEMINI_API_KEY}]
    if config.GEMINI_API_KEY.startswith("AQ."):
        attempts.append({"_query_key": True})  # some Vertex Express setups only accept the key as a query parameter
    for attempt in range(3):
        for mode in attempts:
            try:
                u = url + ("?key=" + config.GEMINI_API_KEY if mode.get("_query_key") else "")
                headers = {"Content-Type": "application/json", **{k: v for k, v in mode.items() if not k.startswith("_")}}
                with urllib.request.urlopen(urllib.request.Request(u, data=data, method="POST", headers=headers), timeout=60) as r:
                    text = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text) if as_json else text
            except Exception:
                continue
        time.sleep(2 * (attempt + 1))
    return None
