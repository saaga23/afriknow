#!/usr/bin/env python3
"""Quick test: single API call to verify connectivity."""
import os
import sys
from pathlib import Path
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ.get("OPENROUTER_API_KEY", ""))

print("Testing OpenRouter connectivity...")
try:
    resp = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Answer with ONLY the letter A. What is 2+2? A) 3 B) 4 C) 5 D) 6"}],
        temperature=0.0,
        max_tokens=10,
        timeout=60,
    )
    content = resp.choices[0].message.content if resp.choices else ""
    usage = getattr(resp, "usage", None)
    print(f"SUCCESS: '{content}'")
    print(f"Usage: prompt={usage.prompt_tokens if usage else 'N/A'}, completion={usage.completion_tokens if usage else 'N/A'}")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
