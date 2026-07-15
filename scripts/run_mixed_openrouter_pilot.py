#!/usr/bin/env python3
"""
Run a 20-item mixed-source pilot on OpenRouter (closed models).

This is a quick proof-of-concept for the source-confound contrast.
Cost: ~$0.05 for 20 items × 4 closed models.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
MIXED_JSON = OUT_DIR / "02_mixed_source_180_items.json"
PILOT_JSON = OUT_DIR / "02_mixed_source_pilot_20.json"

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

MODELS = [
    ("openai/gpt-4o-mini", "gpt-4o-mini", 0.0, 256),
    ("anthropic/claude-3-haiku", "claude-3-haiku", 0.0, 256),
    ("openai/gpt-4.1-nano", "gpt-4.1-nano", 0.0, 256),
    ("google/gemini-2.5-flash-lite", "gemini-2.5-flash-lite", 0.0, 256),
]

MODEL_CLASS = {
    "gpt-4o-mini": "closed",
    "claude-3-haiku": "closed",
    "gpt-4.1-nano": "closed",
    "gemini-2.5-flash-lite": "closed",
}

MAX_RETRIES = 3
BACKOFF = 2.0
REQUEST_TIMEOUT = 60
MAX_FAILURE_RATE = 0.25

PRICE_TABLE = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "openai/gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.60}


def log(msg: str) -> None:
    print(f"[mixed-pilot] {msg}", flush=True)


def build_mcqa_prompt(item):
    lines = ["Answer the following multiple-choice question with ONLY the letter of the correct answer (A, B, C, or D). No explanation is needed.", "", item["q"]]
    for i, c in enumerate(item["ch"]):
        lines.append(f"{chr(65+i)}. {c}")
    lines.extend(["", "Answer:"])
    return "\n".join(lines)


def build_vce_prompt(item, predicted_letter):
    lines = ["You already selected an answer for the question below.",
             "Now provide ONLY your confidence in that answer as an integer from 0 to 100.",
             "No explanation is needed; output just the number.", "", item["q"]]
    for i, c in enumerate(item["ch"]):
        lines.append(f"{chr(65+i)}. {c}")
    lines.extend(["", f"Your selected answer: {predicted_letter}", "", "Confidence (0-100):"])
    return "\n".join(lines)


def clean_raw_text(text, purpose="greedy"):
    if not isinstance(text, str):
        return text
    t = text.strip()
    if not t or t.lower() == "nan":
        return t
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL)
    t = re.sub(r"\s+", " ", t).strip()
    if purpose == "greedy":
        m = re.search(r"\b([A-D])\b", t)
        return m.group(1).upper() if m else "X"
    if purpose == "vce":
        m = re.search(r"\b(\d{1,3})\b", t)
        if m:
            v = int(m.group(1))
            return str(max(0, min(100, v)))
        return "0"
    return t


def parse_letter(text):
    if text is None:
        return "X"
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL)
    for pat in [r"the best answer is\s+([A-D])", r"the correct answer is\s+([A-D])",
                r"final answer\s*[:=]?\s*([A-D])", r"answer\s*[:=]\s*([A-D])", r"answer is\s+([A-D])"]:
        m = re.findall(pat, text, re.IGNORECASE)
        if m:
            return m[-1].upper()
    m = re.search(r"\b([A-D])\b", text)
    if m:
        return m.group(1).upper()
    return "X"


def extract_conf(text):
    if text is None:
        return 0.5
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL)
    m = re.search(r"\b(\d{1,2})\s*[%/\-]\s*\d{1,2}\b", text)
    if m:
        return float(m.group(1)) / 100.0
    m = re.search(r"confidence[:\s]+(\d+)", text, re.IGNORECASE)
    if m:
        return float(m.group(1)) / 100.0
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        v = float(m.group(1))
        return max(0.0, min(1.0, v / 100.0))
    return 0.5


def call_with_retry(client, model_id, messages, temperature, max_tokens, nick, idx, purpose, max_retries=5):
    import time as _time
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp
        except Exception as e:
            last_err = e
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                wait = (2 ** attempt) + (_time.random() if hasattr(_time, 'random') else 0)
                log(f"[OR] {nick} item {idx} {purpose} rate-limited (429). Retry {attempt+1}/{max_retries} in {wait:.1f}s")
                _time.sleep(wait)
            elif "500" in err_str or "502" in err_str or "503" in err_str:
                wait = (2 ** attempt) + 1
                log(f"[OR] {nick} item {idx} {purpose} server error. Retry {attempt+1}/{max_retries} in {wait:.1f}s")
                _time.sleep(wait)
            else:
                raise
    raise last_err


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-items", type=int, default=20, help="Number of items to run")
    args = parser.parse_args()

    # Load .env
    env_path = ROOT.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    try:
        from openai import OpenAI
    except ImportError:
        log("ERROR: openai package not installed.")
        return

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        log("ERROR: OPENROUTER_API_KEY not set.")
        return

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    # Load mixed-source items and sample
    with open(MIXED_JSON, encoding="utf-8") as f:
        mixed_data = json.load(f)
    mixed_items = mixed_data["items"]

    # Sample n items, balanced by region
    africa = [it for it in mixed_items if it["region"] == "Africa"]
    europe = [it for it in mixed_items if it["region"] == "Europe"]
    n_per_region = args.n_items // 2
    random.shuffle(africa)
    random.shuffle(europe)
    items = africa[:n_per_region] + europe[:n_per_region]
    random.shuffle(items)

    log(f"Running {args.n_items} mixed-source items ({n_per_region} Africa + {n_per_region} Europe)")

    all_rows = []
    for model_id, nick, temp, max_tokens in MODELS:
        log(f"[OR] {nick} on {len(items)} mixed-source items ...")
        for idx, item in enumerate(items):
            # Greedy MCQA
            g_prompt = build_mcqa_prompt(item)
            try:
                g_resp = call_with_retry(client, model_id, [{"role": "user", "content": g_prompt}], temp, max_tokens, nick, idx, "greedy")
                g_text = (g_resp.choices[0].message.content or "") if g_resp.choices else ""
                g_pred = parse_letter(g_text)
            except Exception as e:
                log(f"[OR] {nick} item {idx} greedy FAILED: {e}")
                g_pred = "X"
                g_text = ""

            # VCE
            v_prompt = build_vce_prompt(item, g_pred)
            try:
                v_resp = call_with_retry(client, model_id, [{"role": "user", "content": v_prompt}], temp, 512, nick, idx, "vce")
                v_text = (v_resp.choices[0].message.content or "") if v_resp.choices else ""
                vce = extract_conf(v_text)
            except Exception as e:
                log(f"[OR] {nick} item {idx} VCE FAILED: {e}")
                vce = 0.5
                v_text = ""

            gold_idx = item.get("a", 0)
            gold = chr(65 + int(gold_idx))
            base = {
                "item_idx": idx,
                "id": item.get("id"),
                "qid": item.get("qid", item.get("id")),
                "region": item.get("region", ""),
                "model": nick,
                "model_id": model_id,
                "model_class": MODEL_CLASS.get(nick, "unknown"),
                "correct_letter": gold,
                "cat": item.get("cat", ""),
                "diff": item.get("diff", ""),
                "source": item.get("source", ""),
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            all_rows.append({**base, "purpose": "greedy", "pred": g_pred,
                             "correct": int(g_pred == gold), "vce": None,
                             "sc_agree": None, "cocoa_fixed": None, "greedy_text": clean_raw_text(g_text, "greedy")})
            all_rows.append({**base, "purpose": "vce", "pred": g_pred,
                             "correct": int(g_pred == gold), "vce": vce,
                             "sc_agree": None, "cocoa_fixed": 0.5 * vce + 0.5, "greedy_text": clean_raw_text(v_text, "vce")})

    df = pd.DataFrame(all_rows)
    out_path = OUT_DIR / "03_openrouter_outputs_mixed_pilot.csv"
    df.to_csv(out_path, index=False)
    log(f"Saved {out_path} ({len(df)} rows)")

    # Quick stats
    vce = df[df["purpose"] == "vce"]
    wrong_af = vce[(vce["region"] == "Africa") & (vce["correct"] == 0)]
    wrong_eu = vce[(vce["region"] == "Europe") & (vce["correct"] == 0)]
    log(f"Africa wrong-answer VCE: {wrong_af['vce'].mean():.3f} (n={len(wrong_af)})")
    log(f"Europe wrong-answer VCE: {wrong_eu['vce'].mean():.3f} (n={len(wrong_eu)})")


if __name__ == "__main__":
    main()
