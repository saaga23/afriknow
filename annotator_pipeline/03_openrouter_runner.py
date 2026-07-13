#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 3a: OpenRouter Lane (closed models)

Runs the 2 CLOSED cheap models on OpenRouter:
  - openai/gpt-4o-mini
  - anthropic/claude-3-haiku

Same prompts/schema as the Modal lane (03_modal_runner.py) so the two
lanes merge trivially into 03_model_outputs.csv with a `provider` tag.

Outputs:
  annotator_pipeline/outputs/03_openrouter_outputs.csv
  annotator_pipeline/outputs/03_openrouter_cost_history.csv
  annotator_pipeline/outputs/03_openrouter_manifest.json
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
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLED_JSON = OUT_DIR / "02_sampled_items.json"

# All 5 models on OpenRouter for this run (closed + open).
# The 3 open models are TARGETED for Modal long-term; run here on OpenRouter
# to keep momentum while Modal is unavailable. Model class is tagged below.
MODELS = [
    ("openai/gpt-4o-mini", "gpt-4o-mini", 0.0, 256),
    ("anthropic/claude-3-haiku", "claude-3-haiku", 0.0, 256),
    ("deepseek/deepseek-v3.2", "deepseek-v3.2", 0.8, 256),
    ("qwen/qwen3-235b-a22b-2507", "qwen3-235b", 0.8, 256),
    ("meta-llama/llama-3.3-70b-instruct", "llama-3.3-70b", 0.8, 256),
]

# nick -> intended compute class (for provenance; Modal is the long-term home for "open")
MODEL_CLASS = {
    "gpt-4o-mini": "closed",
    "claude-3-haiku": "closed",
    "deepseek-v3.2": "open",
    "qwen3-235b": "open",
    "llama-3.3-70b": "open",
}

RESERVE_POOL = [
    ("openai/gpt-4.1-nano", "gpt-4.1-nano", 0.0, 256),
    ("anthropic/claude-haiku-4.5", "claude-haiku-4.5", 0.0, 256),
    ("google/gemini-2.5-flash-lite", "gemini-2.5-flash-lite", 0.8, 256),
]

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

MAX_RETRIES = 3
BACKOFF = 2.0
REQUEST_TIMEOUT = 60
MAX_FAILURE_RATE = 0.25
CHECKPOINT_EVERY = 10
COST_CAP_USD = 2.0
DRY_RUN = False

PRICE_TABLE = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "openai/gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "anthropic/claude-haiku-4.5": {"input": 0.80, "output": 4.00},
    "google/gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "deepseek/deepseek-v3.2": {"input": 0.2288, "output": 0.3432},
    "qwen/qwen3-235b-a22b-2507": {"input": 0.09, "output": 0.10},
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.10, "output": 0.32},
}
DEFAULT_PRICE = {"input": 0.15, "output": 0.60}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log(msg: str) -> None:
    print(f"[or-lane] {msg}", flush=True)

# Load .env if present (no dotenv dependency)
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

if not os.environ.get("OPENROUTER_API_KEY"):
    log("WARN: OPENROUTER_API_KEY not set; set it in .env or env before running.")

from openai import OpenAI, APIError, APITimeoutError
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ.get("OPENROUTER_API_KEY", ""))

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

class CostTracker:
    def __init__(self, cap):
        self.cap = cap; self.spent = 0.0; self.history = []
    def estimate(self, model, it, ot):
        p = PRICE_TABLE.get(model, DEFAULT_PRICE)
        return (it * p["input"] + ot * p["output"]) / 1e6
    def would_exceed(self, model, it, ot):
        return (self.spent + self.estimate(model, it, ot)) > self.cap
    def add(self, model, it, ot, purpose):
        c = self.estimate(model, it, ot); self.spent += c
        self.history.append({"model": model, "purpose": purpose, "input_tokens": it,
                             "output_tokens": ot, "cost_usd": c, "cumulative_usd": self.spent,
                             "timestamp": datetime.now(timezone.utc).isoformat()})
        return c
    def check(self):
        if self.spent >= self.cap:
            raise RuntimeError(f"Cost cap ${self.cap:.2f} exceeded (spent ${self.spent:.4f}).")

cost_tracker = CostTracker(COST_CAP_USD)

def chat_complete(model_id, prompt, temperature, max_tokens=None, purpose="unknown"):
    cost_tracker.check()
    it_est = len(prompt.split()) + 20
    ot_est = max_tokens if max_tokens is not None else 64
    if cost_tracker.would_exceed(model_id, it_est, ot_est):
        raise RuntimeError(f"Call to {model_id} would exceed cap.")
    kwargs = {"model": model_id, "messages": [{"role": "user", "content": prompt}],
              "temperature": temperature, "timeout": REQUEST_TIMEOUT}
    if model_id.startswith(("openai/gpt-5", "openai/o1", "openai/o3", "openai/o4")):
        kwargs["max_completion_tokens"] = max_tokens if max_tokens is not None else 4096
    elif max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content if resp.choices else ""
    usage = getattr(resp, "usage", None)
    it = getattr(usage, "prompt_tokens", it_est) if usage else it_est
    ot = getattr(usage, "completion_tokens", len(content.split())) if usage else max(1, len(content.split()))
    cost_tracker.add(model_id, it, ot, purpose)
    return content

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    global DRY_RUN
    DRY_RUN = args.dry_run

    with open(SAMPLED_JSON, encoding="utf-8") as f:
        items = json.load(f)["items"]
    log(f"Loaded {len(items)} sampled items")

    if args.smoke:
        items = items[:1]
        log("SMOKE MODE: 1 item per model")

    # Preflight
    preflight_ok = {}
    if DRY_RUN:
        for model_id, nick, *_ in MODELS + RESERVE_POOL:
            preflight_ok[nick] = True
    else:
        for model_id, nick, temp, max_tok in MODELS + RESERVE_POOL:
            ok = False
            for probe in items[:2]:
                try:
                    c = chat_complete(model_id, build_mcqa_prompt(probe), temp, max_tok, "preflight")
                    ok = parse_letter(c) in {"A", "B", "C", "D"}
                    if ok:
                        break
                except Exception as e:
                    log(f"Preflight {nick}: {e}")
            preflight_ok[nick] = ok
            log(f"Preflight {nick}: {'OK' if ok else 'FAILED'}")

    active = [m for m in MODELS if preflight_ok.get(m[1], False)]
    for model_id, nick, temp, max_tok in RESERVE_POOL:
        if preflight_ok.get(nick, False) and len(active) < 2:
            active.append((model_id, nick, temp, max_tok))
    if len(active) < 1:
        raise RuntimeError("No models passed preflight.")
    log(f"Active models: {[m[1] for m in active]}")

    if DRY_RUN:
        log("DRY RUN: synthesizing outputs (no network).")
        rng = random.Random(SEED)
        results = []
        for it in items:
            for model_id, nick, temp, max_tok in active:
                pred = rng.choice(["A","B","C","D"]); vce = round(rng.uniform(0.3,0.99),2)
                base = {"item_idx":0,"id":it.get("id"),"qid":it.get("qid",it.get("id")),
                        "region":it.get("region",""),"model":nick,"model_id":model_id,
                        "model_class": MODEL_CLASS.get(nick, "unknown"),
                        "correct_letter":it.get("answer","A"),"cat":it.get("cat",""),
                        "diff":it.get("diff",""),"source":it.get("source",""),
                        "input_tokens":100,"output_tokens":5,"cost_usd":0.0001,
                        "timestamp":datetime.now(timezone.utc).isoformat()}
                results.append({**base,"purpose":"greedy","pred":pred,"correct":int(pred==it.get("answer","A")),
                                "vce":None,"sc_agree":None,"cocoa_fixed":None,"greedy_text":"dry-run"})
                results.append({**base,"purpose":"vce","pred":pred,"correct":int(pred==it.get("answer","A")),
                                "vce":vce,"sc_agree":None,"cocoa_fixed":0.5 * vce + 0.5,"greedy_text":"dry-run"})
        df = pd.DataFrame(results)
        df.to_csv(OUT_DIR / "03_openrouter_outputs.csv", index=False)
        log(f"Saved 03_openrouter_outputs.csv ({len(df)} rows, dry-run)")
        return

    results = []
    failures = defaultdict(int)
    isolated = set()
    for idx, item in enumerate(items):
        for model_id, nick, temp, max_tok in active:
            if nick in isolated:
                continue
            # Greedy
            g_ok = False
            for attempt in range(MAX_RETRIES):
                try:
                    c = chat_complete(model_id, build_mcqa_prompt(item), temp, max_tok, "greedy")
                    pred = parse_letter(c); g_ok = True
                    base = {"item_idx":idx,"id":item.get("id"),"qid":item.get("qid",item.get("id")),
                            "region":item.get("region",""),"model":nick,"model_id":model_id,
                            "model_class": MODEL_CLASS.get(nick, "unknown"),
                            "correct_letter":item.get("answer","A"),"cat":item.get("cat",""),
                            "diff":item.get("diff",""),"source":item.get("source",""),
                            "input_tokens":cost_tracker.history[-1]["input_tokens"] if cost_tracker.history else 100,
                            "output_tokens":cost_tracker.history[-1]["output_tokens"] if cost_tracker.history else 5,
                            "cost_usd":cost_tracker.history[-1]["cost_usd"] if cost_tracker.history else 0.0,
                            "timestamp":datetime.now(timezone.utc).isoformat()}
                    results.append({**base,"purpose":"greedy","pred":pred,
                                    "correct":int(pred==item.get("answer","A")),"vce":None,
                                    "sc_agree":None,"cocoa_fixed":None,"greedy_text":clean_raw_text(c, "greedy")})
                    break
                except Exception as e:
                    log(f"  {nick} item {idx} greedy attempt {attempt+1}: {e}")
                    failures[nick]+=1; time.sleep(BACKOFF*(attempt+1))
            if not g_ok:
                continue
            # VCE
            v_ok = False
            for attempt in range(MAX_RETRIES):
                try:
                    vc = chat_complete(model_id, build_vce_prompt(item, results[-1]["pred"]), 0.0, 512, "vce")
                    vce = extract_conf(vc); v_ok = True
                results.append({**base,"purpose":"vce","pred":results[-1]["pred"],
                                "correct":int(results[-1]["pred"]==item.get("answer","A")),
                                "vce":vce,"sc_agree":None,"cocoa_fixed":0.5 * vce + 0.5,"greedy_text":clean_raw_text(vc, "vce")})
                    break
                except Exception as e:
                    log(f"  {nick} item {idx} VCE attempt {attempt+1}: {e}")
                    failures[nick]+=1; time.sleep(BACKOFF*(attempt+1))
            if not v_ok:
                log(f"  {nick} item {idx}: VCE FAILED")
            if (idx+1) % CHECKPOINT_EVERY == 0:
                pd.DataFrame(results).to_csv(OUT_DIR / f"03_or_checkpoint_{nick}_{idx+1}.csv", index=False)
            cost_tracker.check()
            if failures[nick] / max(1, sum(failures.values())) > MAX_FAILURE_RATE:
                isolated.add(nick); log(f"Model {nick} isolated.")

    df = pd.DataFrame(results)
    df.to_csv(OUT_DIR / "03_openrouter_outputs.csv", index=False)
    log(f"Saved 03_openrouter_outputs.csv ({len(df)} rows)")

    pd.DataFrame(cost_tracker.history).to_csv(OUT_DIR / "03_openrouter_cost_history.csv", index=False)
    log(f"Saved 03_openrouter_cost_history.csv (${cost_tracker.spent:.4f})")

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": __file__, "provider": "openrouter", "seed": SEED,
        "models_active": [m[1] for m in active], "models_isolated": list(isolated),
        "n_items": len(items), "n_rows": len(df), "total_cost_usd": round(cost_tracker.spent, 6),
        "input_hash": sha256(SAMPLED_JSON),
        "output_hash": sha256(OUT_DIR / "03_openrouter_outputs.csv"),
        "schema_match_modal": True,
    }
    with open(OUT_DIR / "03_openrouter_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log("Manifest written. Done.")

if __name__ == "__main__":
    main()
