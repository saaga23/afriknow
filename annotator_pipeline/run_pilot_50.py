#!/usr/bin/env python3
"""
AfriKnow — 50-item GM-only pilot (OpenRouter + Modal)

Runs 7 models on 50 GM-only items:
  OpenRouter (closed): claude-3-haiku, gpt-4o-mini, gpt-4.1-nano, gemini-2.5-flash-lite
  Modal (open):         deepseek-v3.2, qwen3-235b, llama-3.3-70b

Outputs:
  annotator_pipeline/outputs/pilot_or_outputs.csv
  annotator_pipeline/outputs/pilot_modal_outputs.csv
  annotator_pipeline/outputs/pilot_merged.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs"
PILOT_ITEMS = OUT_DIR / "02_pilot_50_items.json"

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Load .env
_env_path = ROOT.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

OPENROUTER_MODELS = [
    ("openai/gpt-4o-mini", "gpt-4o-mini", 0.0, 256, 64),
    ("anthropic/claude-3-haiku", "claude-3-haiku", 0.0, 256, 64),
    ("openai/gpt-4.1-nano", "gpt-4.1-nano", 0.0, 256, 64),
    ("google/gemini-2.5-flash-lite", "gemini-2.5-flash-lite", 0.0, 256, 64),
]

MODAL_MODELS = [
    ("deepseek/deepseek-v3.2", "deepseek-v3.2"),
    ("qwen/qwen3-235b-a22b-2507", "qwen3-235b"),
    ("meta-llama/llama-3.3-70b-instruct", "llama-3.3-70b"),
]

PRICE_TABLE = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "openai/gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "deepseek/deepseek-v3.2": {"input": 0.2288, "output": 0.3432},
    "qwen/qwen3-235b-a22b-2507": {"input": 0.09, "output": 0.10},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.10, "output": 0.32},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.60}


def log(msg: str) -> None:
    print(f"[pilot] {msg}", flush=True)


def load_items():
    with open(PILOT_ITEMS, encoding="utf-8") as f:
        data = json.load(f)
    return data["items"]


# ---- Prompts (shared with existing lanes) ----

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
    t = re.sub(r"```.*?```", "", t, flags=re.DOTALL)
    t = re.sub(r"`+", "", t)
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
    m = re.search(r"confidence[:\s]+(\d+)", text, re.IGNORECASE)
    if m:
        return float(m.group(1)) / 100.0
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        v = float(m.group(1))
        return max(0.0, min(1.0, v / 100.0))
    return 0.5


# ---- OpenRouter lane ----

def call_with_retry(client, model_id, messages, temperature, max_tokens, nick, idx, purpose, max_retries=5):
    """Call OpenRouter API with exponential backoff on rate limits."""
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
            if "429" in err_str or "rate limit" in err_str.lower() or "tokens per min" in err_str.lower():
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


def run_openrouter_pilot(items):
    try:
        from openai import OpenAI
    except ImportError:
        log("ERROR: openai package not installed. Run: pip install openai")
        return []

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        log("ERROR: OPENROUTER_API_KEY not set in environment")
        return []

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    all_rows = []
    cost_history = []

    for model_id, nick, temp, max_tokens_g, max_tokens_v in OPENROUTER_MODELS:
        log(f"[OR] {nick} on {len(items)} items ...")
        for idx, item in enumerate(items):
            # Greedy MCQA
            g_prompt = build_mcqa_prompt(item)
            try:
                g_resp = call_with_retry(client, model_id, [{"role": "user", "content": g_prompt}], temp, max_tokens_g, nick, idx, "greedy")
                g_text = (g_resp.choices[0].message.content or "") if g_resp.choices else ""
                g_pred = parse_letter(g_text)
                g_it = g_resp.usage.prompt_tokens if g_resp.usage else 0
                g_ot = g_resp.usage.completion_tokens if g_resp.usage else 0
                g_cost = (g_it * PRICE_TABLE.get(model_id, DEFAULT_PRICE)["input"] +
                          g_ot * PRICE_TABLE.get(model_id, DEFAULT_PRICE)["output"]) / 1e6
            except Exception as e:
                log(f"[OR] {nick} item {idx} greedy FAILED: {e}")
                g_pred = "X"
                g_text = ""
                g_it = g_ot = 0
                g_cost = 0.0

            # VCE
            v_prompt = build_vce_prompt(item, g_pred)
            try:
                v_resp = call_with_retry(client, model_id, [{"role": "user", "content": v_prompt}], temp, max_tokens_v, nick, idx, "vce")
                v_text = (v_resp.choices[0].message.content or "") if v_resp.choices else ""
                vce = extract_conf(v_text)
                v_it = v_resp.usage.prompt_tokens if v_resp.usage else 0
                v_ot = v_resp.usage.completion_tokens if v_resp.usage else 0
                v_cost = (v_it * PRICE_TABLE.get(model_id, DEFAULT_PRICE)["input"] +
                          v_ot * PRICE_TABLE.get(model_id, DEFAULT_PRICE)["output"]) / 1e6
            except Exception as e:
                log(f"[OR] {nick} item {idx} VCE FAILED: {e}")
                v_text = ""
                vce = 0.5
                v_it = v_ot = 0
                v_cost = 0.0

            gold_idx = item.get("a", 0)
            gold = chr(65 + int(gold_idx))  # 0->A, 1->B, 2->C, 3->D
            base = {
                "item_idx": idx,
                "id": item.get("id"),
                "qid": item.get("qid", item.get("id")),
                "region": item.get("region", ""),
                "model": nick,
                "model_id": model_id,
                "model_class": "closed",
                "correct_letter": gold,
                "cat": item.get("cat", ""),
                "diff": item.get("diff", ""),
                "source": item.get("source", ""),
                "input_tokens": g_it + v_it,
                "output_tokens": g_ot + v_ot,
                "cost_usd": round(g_cost + v_cost, 6),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "openrouter",
            }

            all_rows.append({**base, "purpose": "greedy", "pred": g_pred,
                             "correct": int(g_pred == gold), "vce": None,
                             "sc_agree": None, "cocoa_fixed": None, "greedy_text": g_text})
            all_rows.append({**base, "purpose": "vce", "pred": g_pred,
                             "correct": int(g_pred == gold), "vce": vce,
                             "sc_agree": None, "cocoa_fixed": 0.5 * vce + 0.5, "greedy_text": v_text})

            cost_history.append({
                "model": model_id, "nick": nick, "item_idx": idx,
                "purpose": "greedy+vc", "input_tokens": g_it + v_it,
                "output_tokens": g_ot + v_ot, "cost_usd": round(g_cost + v_cost, 6),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            if (idx + 1) % 10 == 0:
                log(f"[OR] {nick}: {idx+1}/{len(items)} items done")

        log(f"[OR] {nick}: completed {len(items)} items")

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_DIR / "pilot_or_outputs.csv", index=False)
    log(f"Saved pilot_or_outputs.csv ({len(df)} rows)")

    cost_df = pd.DataFrame(cost_history)
    cost_df.to_csv(OUT_DIR / "pilot_or_cost_history.csv", index=False)
    log(f"Saved pilot_or_cost_history.csv ({len(cost_df)} rows)")

    return all_rows


# ---- Modal lane (smoke first) ----

def run_modal_smoke(items):
    """Run 1 item on llama-3.3-70b via Modal to test config."""
    log("[Modal] Attempting smoke test on llama-3.3-70b ...")
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "annotator_pipeline" / "03_modal_runner.py"),
             "--smoke"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "MODAL_TOKEN": os.environ.get("MODAL_TOKEN", ""),
                 "MODAL_API_KEY": os.environ.get("MODAL_API_KEY", "")},
        )
        log(f"[Modal] stdout: {result.stdout[-500:] if result.stdout else 'None'}")
        if result.stderr:
            log(f"[Modal] stderr: {result.stderr[-500:]}")
        return result.returncode == 0
    except Exception as e:
        log(f"[Modal] Smoke test exception: {e}")
        return False


def run_modal_full(items):
    """Run all 50 items on all 3 open models via Modal."""
    log("[Modal] Running full 50-item pilot on open models ...")
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "annotator_pipeline" / "03_modal_runner.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=7200,
            env={**os.environ, "MODAL_TOKEN": os.environ.get("MODAL_TOKEN", ""),
                 "MODAL_API_KEY": os.environ.get("MODAL_API_KEY", "")},
        )
        log(f"[Modal] stdout: {result.stdout[-1000:] if result.stdout else 'None'}")
        if result.stderr:
            log(f"[Modal] stderr: {result.stderr[-1000:]}")
        return result.returncode == 0
    except Exception as e:
        log(f"[Modal] Full run exception: {e}")
        return False


# ---- Merge and validate ----

def merge_and_validate(or_rows, modal_success):
    or_df = pd.DataFrame(or_rows) if or_rows else pd.DataFrame()
    modal_path = OUT_DIR / "03_modal_outputs.csv"

    if modal_success and modal_path.exists():
        modal_df = pd.read_csv(modal_path)
        # Filter to our 50 pilot items
        modal_df = modal_df[modal_df["id"].isin([it["id"] for it in load_items()])]
        merged = pd.concat([or_df, modal_df], ignore_index=True)
        log(f"Merged: {len(or_df)} OR rows + {len(modal_df)} Modal rows = {len(merged)} total")
    else:
        merged = or_df
        log("Modal data not available; using OpenRouter only")

    if len(merged) == 0:
        log("ERROR: No data to validate")
        return None

    # Basic validation
    n_items = merged["id"].nunique()
    n_models = merged["model"].nunique()
    n_rows = len(merged)
    expected_rows = n_items * n_models * 2  # greedy + vce

    log(f"Validation: {n_items} unique items, {n_models} models, {n_rows} rows (expected ~{expected_rows})")

    parse_fails = len(merged[merged["pred"] == "X"])
    wrong_answers = len(merged[merged["correct"] == 0])
    vce_nulls = merged["vce"].isna().sum()

    log(f"Parse failures: {parse_fails}")
    log(f"Wrong answers: {wrong_answers}")
    log(f"VCE nulls: {vce_nulls}")

    merged.to_csv(OUT_DIR / "pilot_merged.csv", index=False)
    log(f"Saved pilot_merged.csv ({len(merged)} rows)")
    return merged


# ---- Main ----

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modal-only", action="store_true", help="Run Modal lane only")
    parser.add_argument("--or-only", action="store_true", help="Run OpenRouter lane only")
    parser.add_argument("--skip-modal", action="store_true", help="Skip Modal (use OR only)")
    parser.add_argument("--skip-or", action="store_true", help="Skip OpenRouter (use Modal only)")
    args = parser.parse_args()

    items = load_items()
    log(f"Loaded {len(items)} pilot items (25 Africa + 25 Europe)")

    or_rows = []
    modal_success = False

    if not args.skip_or and not args.modal_only:
        or_rows = run_openrouter_pilot(items)

    if not args.skip_modal and not args.or_only:
        smoke_ok = run_modal_smoke(items)
        if smoke_ok:
            modal_success = run_modal_full(items)
        else:
            log("[Modal] Smoke test failed; skipping full Modal run")
            log("[Modal] Common causes: HF_TOKEN invalid, vLLM arch unsupported, GPU quota")

    merge_and_validate(or_rows, modal_success)


if __name__ == "__main__":
    main()
