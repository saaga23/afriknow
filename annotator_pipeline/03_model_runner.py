#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 3: Model Runner

Runs 5 models on the 120-item stratified sample:
  - OpenRouter lane: gpt-4o-mini, claude-3-haiku
  - Modal/OpenRouter lane: deepseek-v3.2, qwen3-235b, llama-3.3-70b

Uses the same hardened pipeline patterns from phase4b_gm_only_run.ipynb:
  - Preflight checks
  - Output-constrained prompts (letter-only MCQA, integer-only VCE)
  - Cost tracking with cap
  - Checkpointing every N items
  - Reserve substitution on failure
  - Raw-output forensics logging

Outputs:
  annotator_pipeline/outputs/
    03_model_outputs.csv
    03_cost_history.csv
    03_raw_outputs.csv
    03_model_run_manifest.json
"""

from __future__ import annotations

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
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLED_JSON = OUT_DIR / "02_sampled_items.json"
METRICS_PY = ROOT / "afriknow_phase0_metrics.py"

# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log(msg: str) -> None:
    print(f"[models] {msg}")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

MODELS = [
    ("openai/gpt-4o-mini", "gpt-4o-mini", 0.0, 256),
    ("anthropic/claude-3-haiku", "claude-3-haiku", 0.0, 256),
    ("deepseek/deepseek-v3.2", "deepseek-v3.2", 0.8, 256),
    ("qwen/qwen3-235b-a22b-2507", "qwen3-235b", 0.8, 256),
    ("meta-llama/llama-3.3-70b-instruct", "llama-3.3-70b", 0.8, 256),
]

RESERVE_POOL = [
    ("openai/gpt-4.1-nano", "gpt-4.1-nano", 0.0, 256),
    ("google/gemini-2.5-flash-lite", "gemini-2.5-flash-lite", 0.8, 256),
    ("google/gemma-4-31b-it", "gemma-4-31b", 0.8, 256),
    ("anthropic/claude-sonnet-4.6", "claude-sonnet-4.6", 0.0, 256),
]

N_SC_SAMPLES = 0  # annotator run: no self-consistency needed
MAX_RETRIES = 3
BACKOFF = 2.0
REQUEST_TIMEOUT = 60
MAX_FAILURE_RATE = 0.25
CHECKPOINT_EVERY = 10
COST_CAP_USD = 2.0
SKIP_FAILED_PREFLIGHT = True

PRICE_TABLE = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "deepseek/deepseek-v3.2": {"input": 0.2288, "output": 0.3432},
    "qwen/qwen3-235b-a22b-2507": {"input": 0.09, "output": 0.10},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.10, "output": 0.32},
    "openai/gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "google/gemma-4-31b-it": {"input": 0.12, "output": 0.35},
    "anthropic/claude-sonnet-4.6": {"input": 3.0, "output": 15.0},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.60}
DRY_RUN = False

import argparse
_parser = argparse.ArgumentParser(description="AfriKnow model runner (Phase 3)")
_parser.add_argument("--dry-run", action="store_true", help="produce synthetic outputs without API calls")
_args, _ = _parser.parse_known_args()
DRY_RUN = _args.dry_run
if DRY_RUN:
    log("DRY RUN: no network calls will be made.")

# ---------------------------------------------------------------------------
# Metric helpers (inline to avoid import issues)
# ---------------------------------------------------------------------------
sys_path_added = False
try:
    import sys
    sys.path.insert(0, str(ROOT))
    from afriknow_phase0_metrics import extract_conf
    sys_path_added = True
except Exception as e:
    log(f"WARN: could not import metrics module: {e}")
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
        m = re.search(r"\b(\d{1,2})\b", text)
        if m:
            v = float(m.group(1))
            return max(0.0, min(1.0, v / 100.0))
        return 0.5

def parse_letter(text):
    if text is None:
        return "X"
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL)
    answer_patterns = [
        r"the best answer is\s+([A-D])\b",
        r"the correct answer is\s+([A-D])\b",
        r"final answer\s*[:=]?\s*([A-D])\b",
        r"answer\s*[:=]\s+([A-D])\b",
        r"answer is\s+([A-D])\b",
    ]
    for pat in answer_patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            return matches[-1].upper()
    m = re.search(r"\b([A-D])\b", text)
    if m:
        return m.group(1).upper()
    if text.strip() and text.strip()[0].upper() in "ABCD":
        return text.strip()[0].upper()
    return "X"

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

# ---------------------------------------------------------------------------
# Load sampled items
# ---------------------------------------------------------------------------
log("Loading sampled items...")
with open(SAMPLED_JSON, encoding="utf-8") as f:
    sample_data = json.load(f)
items = sample_data["items"]
log(f"Loaded {len(items)} items ({sum(1 for i in items if i['region']=='Africa')} Africa / {sum(1 for i in items if i['region']=='Europe')} Europe)")

# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI, APIError, APITimeoutError
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
    )
    if not os.environ.get("OPENROUTER_API_KEY"):
        log("WARN: OPENROUTER_API_KEY not set; set it before running.")
except Exception as e:
    log(f"FATAL: cannot import OpenAI client: {e}")
    raise

# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------
class CostTracker:
    def __init__(self, cap):
        self.cap = cap
        self.spent = 0.0
        self.history = []

    def estimate(self, model, input_tokens, output_tokens):
        p = PRICE_TABLE.get(model, DEFAULT_PRICE)
        return (input_tokens * p["input"] + output_tokens * p["output"]) / 1e6

    def would_exceed(self, model, input_tokens, output_tokens):
        return (self.spent + self.estimate(model, input_tokens, output_tokens)) > self.cap

    def add(self, model, input_tokens, output_tokens, purpose):
        cost = self.estimate(model, input_tokens, output_tokens)
        self.spent += cost
        self.history.append({
            "model": model, "purpose": purpose,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "cost_usd": cost, "cumulative_usd": self.spent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return cost

    def check(self):
        if self.spent >= self.cap:
            raise RuntimeError(f"Cost cap ${self.cap:.2f} exceeded (spent ${self.spent:.4f}).")

cost_tracker = CostTracker(COST_CAP_USD)
RAW_OUTPUTS = []

# ---------------------------------------------------------------------------
# Prompt builders (same as hardened notebook)
# ---------------------------------------------------------------------------
def build_mcqa_prompt(item):
    lines = [
        "Answer the following multiple-choice question with ONLY the letter of the correct answer (A, B, C, or D). No explanation is needed.",
        "",
        item["q"],
    ]
    for i, c in enumerate(item["ch"]):
        lines.append(f"{chr(65+i)}. {c}")
    lines.extend(["", "Answer:"])
    return "\n".join(lines)

def build_vce_prompt(item, predicted_letter):
    lines = [
        "You already selected an answer for the question below.",
        "Now provide ONLY your confidence in that answer as an integer from 0 to 100.",
        "No explanation is needed; output just the number.",
        "",
        item["q"],
    ]
    for i, c in enumerate(item["ch"]):
        lines.append(f"{chr(65+i)}. {c}")
    lines.extend(["", f"Your selected answer: {predicted_letter}", "", "Confidence (0-100):"])
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------
def _token_limit_kwargs(model_id, max_tokens):
    if model_id.startswith(("openai/gpt-5", "openai/o1", "openai/o3", "openai/o4")):
        return {"max_completion_tokens": max_tokens if max_tokens is not None else 4096}
    if max_tokens is not None:
        return {"max_tokens": max_tokens}
    return {}

def chat_complete(model_id, prompt, temperature, max_tokens=None, purpose="unknown"):
    cost_tracker.check()
    prompt_tokens_est = len(prompt.split()) + 20
    output_tokens_est = max_tokens if max_tokens is not None else 64
    if cost_tracker.would_exceed(model_id, prompt_tokens_est, output_tokens_est):
        raise RuntimeError(f"Call to {model_id} would exceed cost cap.")
    kwargs = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "timeout": REQUEST_TIMEOUT,
    }
    kwargs.update(_token_limit_kwargs(model_id, max_tokens))
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content if resp.choices else ""
    usage = getattr(resp, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", prompt_tokens_est) if usage else prompt_tokens_est
    output_tokens = getattr(usage, "completion_tokens", len(content.split())) if usage else max(1, len(content.split()))
    cost_tracker.add(model_id, input_tokens, output_tokens, purpose)
    return content, input_tokens, output_tokens

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
log("Running preflight checks...")
preflight_ok = {}
if DRY_RUN:
    log("DRY RUN: skipping live preflight; marking all starters OK.")
    for model_id, nick, temp, max_tok in MODELS + RESERVE_POOL:
        preflight_ok[nick] = True
else:
    for model_id, nick, temp, max_tok in MODELS + RESERVE_POOL:
        ok = False
        for probe in items[:2]:
            try:
                prompt = build_mcqa_prompt(probe)
                content, _, _ = chat_complete(model_id, prompt, temp, max_tok, purpose="preflight")
                letter = parse_letter(content)
                ok = letter in {"A", "B", "C", "D"}
                if ok:
                    break
            except Exception as e:
                log(f"Preflight {nick}: {e}")
        preflight_ok[nick] = ok
        status = "OK" if ok else "FAILED"
        log(f"Preflight {nick}: {status}")

# Drop failed starters, bring in reserves
active_models = []
reserve_queue = []
for model_id, nick, temp, max_tok in MODELS:
    if preflight_ok.get(nick, False):
        active_models.append((model_id, nick, temp, max_tok))
    else:
        log(f"Starter {nick} failed preflight; marking for reserve substitution.")

for model_id, nick, temp, max_tok in RESERVE_POOL:
    if preflight_ok.get(nick, False) and len(active_models) < 5:
        active_models.append((model_id, nick, temp, max_tok))
        log(f"Reserve {nick} activated.")

if len(active_models) < 3:
    raise RuntimeError(f"Insufficient models passed preflight: {[m[1] for m in active_models]}")

log(f"Active models: {[m[1] for m in active_models]}")

# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------
results = []
failures = defaultdict(int)
isolated = set()

for item_idx, item in enumerate(items):
    item_id = item.get("id", item.get("qid", f"item-{item_idx}"))
    region = item["region"]
    qid = item.get("qid", item_id)
    correct_letter = item["answer"]

    for model_idx, (model_id, nick, temp, max_tok) in enumerate(active_models):
        if nick in isolated:
            continue

        row_base = {
            "item_idx": item_idx,
            "id": item_id,
            "qid": qid,
            "region": region,
            "model": nick,
            "model_id": model_id,
            "correct_letter": correct_letter,
            "cat": item.get("cat", ""),
            "diff": item.get("diff", ""),
            "source": item.get("source", ""),
        }

        # Greedy MCQA
        mcqa_ok = False
        for attempt in range(MAX_RETRIES):
            try:
                prompt = build_mcqa_prompt(item)
                content, inp_tok, out_tok = chat_complete(model_id, prompt, temp, max_tok, purpose="greedy_mcqa")
                pred = parse_letter(content)
                mcqa_ok = True
                row = dict(row_base)
                row.update({
                    "purpose": "greedy",
                    "pred": pred,
                    "correct": int(pred == correct_letter),
                    "vce": None,
                    "sc_agree": None,
                    "cocoa_fixed": None,
                    "greedy_text": clean_raw_text(content, "greedy"),
                    "input_tokens": inp_tok,
                    "output_tokens": out_tok,
                    "cost_usd": cost_tracker.history[-1]["cost_usd"] if cost_tracker.history else 0.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                results.append(row)
                RAW_OUTPUTS.append(row)
                break
            except Exception as e:
                log(f"  {nick} item {item_idx} greedy attempt {attempt+1}: {e}")
                failures[nick] += 1
                time.sleep(BACKOFF * (attempt + 1))

        if not mcqa_ok:
            log(f"  {nick} item {item_idx}: greedy FAILED after {MAX_RETRIES} attempts")
            continue

        # VCE
        vce_ok = False
        vce_pred = results[-1]["pred"] if results else "A"
        for attempt in range(MAX_RETRIES):
            try:
                vce_prompt = build_vce_prompt(item, vce_pred)
                vce_content, inp_tok, out_tok = chat_complete(model_id, vce_prompt, 0.0, 512, purpose="vce")
                vce_val = extract_conf(vce_content)
                vce_ok = True
                row = dict(row_base)
                row.update({
                    "purpose": "vce",
                    "pred": vce_pred,
                    "correct": int(vce_pred == correct_letter),
                    "vce": vce_val,
                    "sc_agree": None,
                    "cocoa_fixed": 0.5 * vce_val + 0.5 * 1.0,
                    "greedy_text": clean_raw_text(vce_content, "vce"),
                    "input_tokens": inp_tok,
                    "output_tokens": out_tok,
                    "cost_usd": cost_tracker.history[-1]["cost_usd"] if cost_tracker.history else 0.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                results.append(row)
                RAW_OUTPUTS.append(row)
                break
            except Exception as e:
                log(f"  {nick} item {item_idx} VCE attempt {attempt+1}: {e}")
                failures[nick] += 1
                time.sleep(BACKOFF * (attempt + 1))

        if not vce_ok:
            log(f"  {nick} item {item_idx}: VCE FAILED")

        # Checkpoint
        if (item_idx + 1) % CHECKPOINT_EVERY == 0:
            ckpt_df = pd.DataFrame(results)
            ckpt_path = OUT_DIR / f"03_checkpoint_{nick}_{item_idx+1}.csv"
            ckpt_df.to_csv(ckpt_path, index=False)
            log(f"Checkpoint saved: {ckpt_path}")

        cost_tracker.check()

        # Isolation guard
        if failures[nick] / max(1, sum(failures.values())) > MAX_FAILURE_RATE:
            isolated.add(nick)
            log(f"Model {nick} isolated due to high failure rate.")

# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------
log("Saving outputs...")

# DRY RUN: if no real results were collected, synthesize a valid output
# using the exact same schema so downstream phases (04, 06) can be validated.
if DRY_RUN and len(results) == 0:
    log("DRY RUN: synthesizing outputs from sampled items (no network).")
    rng = random.Random(SEED)
    active_models = [(m[0], m[1], m[2], m[3]) for m in MODELS]
    for item in items:
        orig_id = item.get("id", item.get("qid", ""))
        gold = item.get("answer", "A")
        for model_id, nick, temp, max_tok in active_models:
            pred = rng.choice(["A", "B", "C", "D"])
            vce = round(rng.uniform(0.3, 0.99), 2)
            base = {
                "item_idx": 0, "id": orig_id, "qid": item.get("qid", orig_id),
                "region": item.get("region", ""), "model": nick, "model_id": model_id,
                "correct_letter": gold, "cat": item.get("cat", ""), "diff": item.get("diff", ""),
                "source": item.get("source", ""), "input_tokens": 100, "output_tokens": 5,
                "cost_usd": 0.0001, "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results.append({**base, "purpose": "greedy", "pred": pred, "correct": int(pred == gold),
                            "vce": None, "sc_agree": None, "cocoa_fixed": None, "greedy_text": "dry-run"})
            results.append({**base, "purpose": "vce", "pred": pred, "correct": int(pred == gold),
                            "vce": vce, "sc_agree": None, "cocoa_fixed": 0.5 * vce + 0.5,
                            "greedy_text": "dry-run"})

results_df = pd.DataFrame(results)
results_df.to_csv(OUT_DIR / "03_model_outputs.csv", index=False)
log(f"Saved 03_model_outputs.csv ({len(results_df)} rows)")

cost_df = pd.DataFrame(cost_tracker.history)
cost_df.to_csv(OUT_DIR / "03_cost_history.csv", index=False)
log(f"Saved 03_cost_history.csv (${cost_tracker.spent:.4f})")

raw_df = pd.DataFrame(RAW_OUTPUTS)
raw_df.to_csv(OUT_DIR / "03_raw_outputs.csv", index=False)
log(f"Saved 03_raw_outputs.csv ({len(raw_df)} rows)")

# Manifest
manifest = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "script": __file__,
    "seed": SEED,
    "models_requested": [m[1] for m in MODELS],
    "models_active": [m[1] for m in active_models],
    "models_isolated": list(isolated),
    "items_evaluated": len(items),
    "total_rows": len(results),
    "total_cost_usd": round(cost_tracker.spent, 6),
    "dry_run": DRY_RUN,
    "sample_input": str(SAMPLED_JSON),
    "sample_input_hash": sha256(SAMPLED_JSON),
    "outputs": {
        "model_outputs": str(OUT_DIR / "03_model_outputs.csv"),
        "cost_history": str(OUT_DIR / "03_cost_history.csv"),
        "raw_outputs": str(OUT_DIR / "03_raw_outputs.csv"),
    },
    "data_hashes": {
        str(SAMPLED_JSON.name): sha256(SAMPLED_JSON),
        str(SAMPLED_JSON): sha256(SAMPLED_JSON),
    },
}
manifest_path = OUT_DIR / "03_model_run_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
log(f"Manifest written to {manifest_path}")
log("Done.")
