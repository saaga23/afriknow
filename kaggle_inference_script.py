#!/usr/bin/env python3
"""
AfriKnow — Kaggle Script Kernel (8 models, 180 mixed-source items)

This script is designed to run on Kaggle as a script kernel.
It uses OpenRouter API with retry logic and cost tracking.

Setup:
1. Attach dataset: abrahamsunday123/afriknow-inference-code
2. Add Kaggle secret: OPENROUTER_API_KEY
3. Run this script
"""

import os
import sys
from pathlib import Path

# Add dataset to path
sys.path.insert(0, "/kaggle/input/afriknow-inference-code")

# Install dependencies
os.system("pip install openai pandas numpy scipy scikit-learn statsmodels -q")

# Import after path setup
from annotator_pipeline.prompts import (
    build_mcqa_prompt,
    build_vce_prompt,
    clean_raw_text,
    parse_letter,
    extract_conf,
    get_gold_letter,
)
from annotator_pipeline.schema import validate_df, REQUIRED_COLUMNS

import argparse
import hashlib
import json
import random
import re
import time
from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd

# ─── Configuration ───────────────────────────────────────────────────────────

OUT_DIR = Path(".")
ITEMS_JSON = Path("/kaggle/input/afriknow-inference-code/02_mixed_source_180_items.json")
OUTPUT_CSV = OUT_DIR / "kaggle_8model_outputs.csv"
COST_HISTORY_CSV = OUT_DIR / "kaggle_8model_cost_history.csv"
MANIFEST_JSON = OUT_DIR / "kaggle_8model_manifest.json"

SEED = 42
random.seed(SEED)

MODELS = [
    ("openai/gpt-4o-mini",           "gpt-4o-mini",       0.0, 256),
    ("anthropic/claude-3-haiku",     "claude-3-haiku",     0.0, 256),
    ("deepseek/deepseek-v3.2",       "deepseek-v3.2",     0.8, 256),
    ("qwen/qwen3-235b-a22b-2507",    "qwen3-235b",        0.8, 256),
    ("meta-llama/llama-3.3-70b-instruct", "llama-3.3-70b", 0.8, 256),
    ("openai/gpt-4.1-nano",          "gpt-4.1-nano",      0.0, 256),

    ("google/gemini-2.5-flash-lite", "gemini-2.5-flash-lite", 0.8, 256),
]

MODEL_CLASS = {
    "gpt-4o-mini": "closed",
    "claude-3-haiku": "closed",
    "deepseek-v3.2": "open",
    "qwen3-235b": "open",
    "llama-3.3-70b": "open",
    "gpt-4.1-nano": "closed",

    "gemini-2.5-flash-lite": "open",
}

PRICE_TABLE = {
    "openai/gpt-4o-mini":           {"input": 0.15,  "output": 0.60},
    "anthropic/claude-3-haiku":     {"input": 0.25,  "output": 1.25},
    "deepseek/deepseek-v3.2":       {"input": 0.2288,"output": 0.3432},
    "qwen/qwen3-235b-a22b-2507":    {"input": 0.09,  "output": 0.10},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.10, "output": 0.32},
    "openai/gpt-4.1-nano":          {"input": 0.10,  "output": 0.40},

    "google/gemini-2.5-flash-lite": {"input": 0.10,  "output": 0.40},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.60}

MAX_RETRIES = 5
BACKOFF_BASE = 2.0
REQUEST_TIMEOUT = 60
MAX_FAILURE_RATE = 0.30
CHECKPOINT_EVERY = 20
COST_CAP_USD = 5.0


# ─── Cost Tracker ────────────────────────────────────────────────────────────

class CostTracker:
    def __init__(self, cap: float):
        self.cap = cap
        self.spent = 0.0
        self.history = []

    def estimate(self, model_id: str, it: int, ot: int) -> float:
        p = PRICE_TABLE.get(model_id, DEFAULT_PRICE)
        return (it * p["input"] + ot * p["output"]) / 1_000_000

    def would_exceed(self, model_id: str, it: int, ot: int) -> bool:
        return (self.spent + self.estimate(model_id, it, ot)) > self.cap

    def add(self, model_id: str, it: int, ot: int, purpose: str) -> float:
        c = self.estimate(model_id, it, ot)
        self.spent += c
        self.history.append({
            "model": model_id,
            "purpose": purpose,
            "input_tokens": it,
            "output_tokens": ot,
            "cost_usd": round(c, 8),
            "cumulative_usd": round(self.spent, 8),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return c

    def check(self):
        if self.spent >= self.cap:
            raise RuntimeError(f"Cost cap ${self.cap:.2f} exceeded (spent ${self.spent:.4f}).")


# ─── OpenRouter Client ───────────────────────────────────────────────────────

def get_openrouter_client():
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        # Fallback: try reading from private dataset
        key_file = Path("/kaggle/input/afriknow-openrouter-key/.env")
        if key_file.exists():
            for line in key_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "OPENROUTER_API_KEY":
                        api_key = v.strip()
                        os.environ["OPENROUTER_API_KEY"] = api_key
                        print("[kaggle] Loaded API key from private dataset fallback")
                        break
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Set as Kaggle secret or upload private dataset.")
    try:
        from openai import OpenAI
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    except ImportError:
        raise RuntimeError("openai package not installed.")


def chat_complete(client, model_id: str, prompt: str, temperature: float, max_tokens: int | None, purpose: str, cost_tracker: CostTracker) -> tuple[str, int, int]:
    cost_tracker.check()
    it_est = len(prompt.split()) + 20
    ot_est = max_tokens if max_tokens is not None else 64
    if cost_tracker.would_exceed(model_id, it_est, ot_est):
        raise RuntimeError(f"Call to {model_id} would exceed cost cap.")

    kwargs = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "timeout": REQUEST_TIMEOUT,
    }
    if model_id.startswith(("openai/gpt-5", "openai/o1", "openai/o3", "openai/o4")):
        kwargs["max_completion_tokens"] = max_tokens if max_tokens is not None else 4096
    elif max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content if resp.choices else ""
            usage = getattr(resp, "usage", None)
            it = getattr(usage, "prompt_tokens", it_est) if usage else it_est
            ot = getattr(usage, "completion_tokens", max(1, len(content.split()))) if usage else max(1, len(content.split()))
            cost_tracker.add(model_id, it, ot, purpose)
            return content, it, ot
        except Exception as e:
            last_err = e
            err_str = str(e)
            wait = BACKOFF_BASE ** attempt + random.uniform(0, 1)
            if "429" in err_str or "rate limit" in err_str.lower():
                print(f"[OR] {model_id} rate-limited (429). Retry {attempt+1}/{MAX_RETRIES} in {wait:.1f}s")
            elif "500" in err_str or "502" in err_str or "503" in err_str:
                print(f"[OR] {model_id} server error. Retry {attempt+1}/{MAX_RETRIES} in {wait:.1f}s")
            else:
                print(f"[OR] {model_id} error: {e}. Retry {attempt+1}/{MAX_RETRIES} in {wait:.1f}s")
            time.sleep(wait)

    raise last_err


# ─── Inference ───────────────────────────────────────────────────────────────

def run_inference(items: list[dict], client, cost_tracker: CostTracker, active_models: list[tuple]) -> list[dict]:
    results = []
    failures = defaultdict(int)
    isolated = set()

    for idx, item in enumerate(items):
        for model_id, nick, temp, max_tok in active_models:
            if nick in isolated:
                continue

            # Greedy pass
            g_pred = "X"
            g_text = ""
            g_it, g_ot = 0, 0
            for attempt in range(MAX_RETRIES):
                try:
                    g_text, g_it, g_ot = chat_complete(
                        client, model_id, build_mcqa_prompt(item), temp, max_tok, "greedy", cost_tracker
                    )
                    g_pred = parse_letter(g_text)
                    if g_pred in {"A", "B", "C", "D"}:
                        break
                except Exception as e:
                    failures[nick] += 1
                    wait = BACKOFF_BASE ** attempt
                    print(f"  {nick} item {idx} greedy attempt {attempt+1}: {e}. Waiting {wait:.1f}s")
                    time.sleep(wait)

            if g_pred == "X":
                continue

            # VCE pass
            vce = 0.5
            v_text = ""
            v_it, v_ot = 0, 0
            for attempt in range(MAX_RETRIES):
                try:
                    v_text, v_it, v_ot = chat_complete(
                        client, model_id, build_vce_prompt(item, g_pred), 0.0, 512, "vce", cost_tracker
                    )
                    vce = extract_conf(v_text)
                    break
                except Exception as e:
                    failures[nick] += 1
                    wait = BACKOFF_BASE ** attempt
                    print(f"  {nick} item {idx} VCE attempt {attempt+1}: {e}. Waiting {wait:.1f}s")
                    time.sleep(wait)

            gold = get_gold_letter(item)
            base = {
                "item_idx": idx,
                "id": item.get("id", ""),
                "qid": item.get("qid", item.get("id", "")),
                "region": item.get("region", ""),
                "model": nick,
                "model_id": model_id,
                "model_class": MODEL_CLASS.get(nick, "unknown"),
                "correct_letter": gold,
                "cat": item.get("cat", ""),
                "diff": item.get("diff", ""),
                "source": item.get("source", ""),
                "input_tokens": g_it + v_it,
                "output_tokens": g_ot + v_ot,
                "cost_usd": round(cost_tracker.history[-1]["cost_usd"] if cost_tracker.history else 0.0, 8),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "openrouter",
            }

            results.append({
                **base,
                "purpose": "greedy",
                "pred": g_pred,
                "correct": int(g_pred == gold),
                "vce": None,
                "sc_agree": None,
                "cocoa_fixed": None,
                "greedy_text": clean_raw_text(g_text, "greedy"),
            })
            results.append({
                **base,
                "purpose": "vce",
                "pred": g_pred,
                "correct": int(g_pred == gold),
                "vce": round(vce, 4),
                "sc_agree": None,
                "cocoa_fixed": round(0.5 * vce + 0.5, 4),
                "greedy_text": clean_raw_text(v_text, "vce"),
            })

            if (idx + 1) % CHECKPOINT_EVERY == 0:
                pd.DataFrame(results).to_csv(OUT_DIR / f"kaggle_checkpoint_{nick}_{idx+1}.csv", index=False)
                print(f"[kaggle] Checkpoint saved: {len(results)} rows at item {idx+1}")

            total_fail = sum(failures.values())
            if total_fail > 0 and failures[nick] / total_fail > MAX_FAILURE_RATE:
                isolated.add(nick)
                print(f"[kaggle] Model {nick} isolated due to high failure rate ({failures[nick]}/{total_fail})")

            cost_tracker.check()

    return results


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-items", type=int, default=None)
    parser.add_argument("--cost-cap", type=float, default=COST_CAP_USD)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if not ITEMS_JSON.exists():
        raise FileNotFoundError(f"Items file not found: {ITEMS_JSON}")
    with open(ITEMS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"]
    if args.n_items is not None:
        items = items[:args.n_items]
    if args.smoke:
        items = items[:1]
    print(f"[kaggle] Loaded {len(items)} items from {ITEMS_JSON.name}")

    client = get_openrouter_client()
    cost_tracker = CostTracker(args.cost_cap)

    # Preflight
    active = []
    for model_id, nick, temp, max_tok in MODELS:
        try:
            c, it, ot = chat_complete(
                client, model_id, build_mcqa_prompt(items[0]), temp, max_tok, "preflight", cost_tracker
            )
            pred = parse_letter(c)
            ok = pred in {"A", "B", "C", "D"}
            print(f"[kaggle] Preflight {nick}: {'OK' if ok else 'FAIL'} (pred={pred}, ${cost_tracker.history[-1]['cost_usd']:.6f})")
            if ok:
                active.append((model_id, nick, temp, max_tok))
        except Exception as e:
            print(f"[kaggle] Preflight {nick}: ERROR — {e}")

    if not active:
        raise RuntimeError("No models passed preflight.")
    print(f"[kaggle] Active models ({len(active)}): {[m[1] for m in active]}")

    t0 = time.time()
    results = run_inference(items, client, cost_tracker, active)
    dt = time.time() - t0

    df = pd.DataFrame(results)
    df = df[REQUIRED_COLUMNS + ["provider"]]
    validate_df(df)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"[kaggle] Saved {OUTPUT_CSV.name} ({len(df)} rows, ${cost_tracker.spent:.4f}, {dt:.1f}s)")

    pd.DataFrame(cost_tracker.history).to_csv(COST_HISTORY_CSV, index=False)
    print(f"[kaggle] Saved {COST_HISTORY_CSV.name} ({len(cost_tracker.history)} records)")

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": "kaggle_inference_script.py",
        "provider": "openrouter",
        "seed": SEED,
        "models_active": [m[1] for m in active],
        "models_total": len(active),
        "n_items": len(items),
        "n_rows": len(df),
        "total_cost_usd": round(cost_tracker.spent, 8),
        "input_hash": sha256(ITEMS_JSON),
        "output_hash": sha256(OUTPUT_CSV),
        "duration_seconds": round(dt, 2),
        "cost_cap_usd": args.cost_cap,
    }
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[kaggle] Saved {MANIFEST_JSON.name}")
    print("[kaggle] DONE.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


if __name__ == "__main__":
    main()
