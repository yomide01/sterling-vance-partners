"""
Sterling & Vance Partners — Proprietary Autonomous Intelligence Core (Python 3.12)
Uses the 100% Free-Tier model internally while never exposing API keys or model names externally.
"""

import os
import json
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_config() -> dict:
    env_path = os.path.join(BASE_DIR, ".env")
    cfg = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                cfg[k.strip()] = v.strip()
    return {
        "api_key": os.environ.get("GEMINI_API_KEY", cfg.get("GEMINI_API_KEY", "")),
        "model": cfg.get("GEMINI_FREE_MODEL", "gemini-3.8-flash"),
        "paystack_ngn_url": cfg.get("PAYSTACK_NGN_URL", "https://paystack.com/pay/sterling-vance-ngn"),
        "global_usd_url": cfg.get("GLOBAL_USD_URL", "https://sterlingvance.lemonsqueezy.com/buy/complete-package"),
    }


def invoke_ai_json(prompt: str) -> dict | None:
    cfg = load_env_config()
    api_key = cfg["api_key"]
    model = cfg["model"]
    if not api_key:
        return None

    # 1. Try 2026 Interactions Endpoint (Free-tier gemini-3.8-flash)
    try:
        req_body = json.dumps({
            "model": model,
            "input": prompt,
            "generation_config": {"response_mime_type": "application/json"}
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            data=req_body,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
                "api-revision": "2026-05-20"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            out_txt = raw.get("output_text")
            if not out_txt and isinstance(raw.get("steps"), list):
                parts = []
                for st in raw["steps"]:
                    if st.get("type") == "model_output":
                        for c in st.get("content", []):
                            if c.get("type") == "text":
                                parts.append(c.get("text", ""))
                out_txt = "\n".join(parts)
            if out_txt:
                return json.loads(out_txt)
    except Exception:
        pass

    # 2. Try Vertex Express Endpoint if AQ.* key
    if api_key.startswith("AQ."):
        try:
            url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model}:generateContent?key={api_key}"
            req_body = json.dumps({
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
                txt = raw["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(txt)
        except Exception:
            pass

    return None
