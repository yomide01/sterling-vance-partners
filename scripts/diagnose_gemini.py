"""Tries the ways a Gemini key can be used and reports the HTTP result (never prints the key)."""
import json, os, urllib.request, urllib.error
KEY = os.environ["GEMINI_API_KEY"]
print("key prefix:", KEY[:3], "length:", len(KEY))
body = json.dumps({"contents": [{"parts": [{"text": "Reply with the single word: ready"}]}]}).encode()
tests = []
for model in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"):
    tests += [("vertex-express header", f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent", {"x-goog-api-key": KEY}),
              ("vertex-express ?key", f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent?key={KEY}", {}),
              ("developer-api header", f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", {"x-goog-api-key": KEY})]
for label, url, h in tests:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", **h}), timeout=40) as r:
            txt = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()[:30]
            res = "OK -> " + txt
    except urllib.error.HTTPError as e:
        try: msg = json.loads(e.read())["error"]["message"][:110]
        except Exception: msg = "?"
        res = f"HTTP {e.code}: {msg.replace(KEY, '***')}"
    except Exception as e:
        res = type(e).__name__
    model = url.split("/models/")[1].split(":")[0]
    line = f"{label} | {model} | {res}"
    print(line)
    print("::notice title=gemini::" + line.replace("\n", " "))
