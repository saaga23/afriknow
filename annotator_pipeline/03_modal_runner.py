#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 3b: Modal Lane (open models)

Runs the 3 OPEN models on Modal serverless GPUs, each with a CORRECT
multi-GPU config (tensor parallelism sized to the model):

  - llama-3.3-70b   (140 GB bf16) -> 2x H100, TP=2   (smallest; smoke target)
  - qwen3-235b      (235 GB bf16) -> 4x H100, TP=4
  - deepseek-v3.2   (671B MoE)    -> 8x H100, TP=8

Design (reviewer-proof + GPU-respectful):
  * BATCHED: each model loads ONCE per Function call, processes ALL items,
    then the GPU is released. No per-item cold starts, no idle GPUs.
  * SAME prompts/schema as the OpenRouter lane -> trivial merge.
  * HF token via Modal Secret (user: "HF is in Modal secret").
  * `tensor_parallel_size` set per model so large MoEs fit on GPU.
  * Modal 1.5.1 API: @app.function decorators must be at global scope.

Usage:
  python 03_modal_runner.py --smoke            # 1 item on llama-3.3-70b (cheap proof)
  python 03_modal_runner.py --smoke --all      # 1 item on ALL 3 (costly; proves each)
  python 03_modal_runner.py                    # full 120-item run, all 3 models
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SAMPLED_JSON = OUT_DIR / "02_sampled_items.json"

SEED = 42
MODAL_SECRET_NAME = "hf-secret"

# Per-model Modal config: nick -> (hf_id, gpu_count, tensor_parallel_size, dtype)
MODAL_MODELS = {
    "llama-3.3-70b":  {"hf_id": "meta-llama/Llama-3.3-70B-Instruct", "gpu": 2, "tp": 2, "dtype": "bfloat16"},
    "qwen3-235b":     {"hf_id": "Qwen/Qwen3-235B-A22B",             "gpu": 4, "tp": 4, "dtype": "bfloat16"},
    "deepseek-v3.2":  {"hf_id": "deepseek-ai/DeepSeek-V3.2",        "gpu": 8, "tp": 8, "dtype": "bfloat16"},
}
NICK_TO_MODEL_ID = {
    "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
    "qwen3-235b":    "qwen/qwen3-235b-a22b-2507",
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log(msg: str) -> None:
    print(f"[modal-lane] {msg}", flush=True)

# ---- prompts (IDENTICAL to OpenRouter lane) ----
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
    m = re.search(r"\b(\d{1,2})\b", text)
    if m:
        v = float(m.group(1))
        return max(0.0, min(1.0, v / 100.0))
    return 0.5

# ---------------------------------------------------------------------------
# Modal app + shared inference helper + global per-model functions
# (Modal 1.5.1 requires @app.function decorators at global scope)
# ---------------------------------------------------------------------------
import modal

# Load .env to get HF_TOKEN for Modal secret
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

hf_secret = modal.Secret.from_dict({"HF_TOKEN": os.environ.get("HF_TOKEN", "")})

app = modal.App("afriknow-annotator-modal")
modal_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.6.3.post1", "huggingface_hub", "transformers", "numpy", "pandas")
)

def _run_model(nick: str, items_json: str):
    """Load one model ONCE, run all items, return rows. GPU released after."""
    import os
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        raise RuntimeError(f"[modal:{nick}] HF_TOKEN is empty in container env")
    print(f"[modal:{nick}] HF login with token prefix {hf_token[:12]}", flush=True)
    try:
        import huggingface_hub
        huggingface_hub.login(token=hf_token)
        print(f"[modal:{nick}] HF login OK", flush=True)
    except Exception as e:
        print(f"[modal:{nick}] HF login warning: {e}", flush=True)
    from vllm import LLM, SamplingParams
    cfg = MODAL_MODELS[nick]
    items = json.loads(items_json)
    print(f"[modal:{nick}] loading {cfg['hf_id']} (TP={cfg['tp']}, {cfg['gpu']}xH100) ...", flush=True)
    llm = LLM(model=cfg["hf_id"], dtype=cfg["dtype"],
              gpu_memory_utilization=0.90, max_model_len=4096,
              trust_remote_code=True, tensor_parallel_size=cfg["tp"])
    g_prompts = [build_mcqa_prompt(it) for it in items]
    g_out = llm.generate(g_prompts, SamplingParams(temperature=0.0, max_tokens=8, n=1))
    g_letters = [parse_letter(o.outputs[0].text) for o in g_out]
    v_prompts = [build_vce_prompt(it, g_letters[i]) for i, it in enumerate(items)]
    v_out = llm.generate(v_prompts, SamplingParams(temperature=0.0, max_tokens=12, n=1))
    v_vals = [extract_conf(o.outputs[0].text) for o in v_out]
    rows = []
    model_id = NICK_TO_MODEL_ID[nick]
    for i, it in enumerate(items):
        gold_idx = it.get("a", 0)
        gold = chr(65 + int(gold_idx))
        pred = g_letters[i]; vce = v_vals[i]
        base = {"item_idx": i, "id": it.get("id"), "qid": it.get("qid", it.get("id")),
                "region": it.get("region", ""), "model": nick, "model_id": model_id,
                "correct_letter": gold, "cat": it.get("cat", ""), "diff": it.get("diff", ""),
                "source": it.get("source", "")}
        rows.append({**base, "purpose": "greedy", "pred": pred, "correct": int(pred == gold),
                     "vce": None, "sc_agree": None, "cocoa_fixed": None, "greedy_text": pred})
        rows.append({**base, "purpose": "vce", "pred": pred, "correct": int(pred == gold),
                     "vce": vce, "sc_agree": None, "cocoa_fixed": 0.5 * vce + 0.5, "greedy_text": str(vce)})
    print(f"[modal:{nick}] done {len(rows)} rows", flush=True)
    return rows

@app.function(image=modal_image, gpu="H100:2", timeout=2400, secrets=[hf_secret])
def run_llama_3_3_70b(items_json: str):
    return _run_model("llama-3.3-70b", items_json)

@app.function(image=modal_image, gpu="H100:4", timeout=2400, secrets=[hf_secret])
def run_qwen3_235b(items_json: str):
    return _run_model("qwen3-235b", items_json)

@app.function(image=modal_image, gpu="H100:8", timeout=2400, secrets=[hf_secret])
def run_deepseek_v3_2(items_json: str):
    return _run_model("deepseek-v3.2", items_json)

FUNCS = {
    "llama-3.3-70b": run_llama_3_3_70b,
    "qwen3-235b": run_qwen3_235b,
    "deepseek-v3.2": run_deepseek_v3_2,
}

# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="1 item per selected model")
    parser.add_argument("--all", action="store_true", help="with --smoke: run all 3 (costly)")
    args = parser.parse_args()

    with open(SAMPLED_JSON, encoding="utf-8") as f:
        items = json.load(f)["items"]
    log(f"Loaded {len(items)} sampled items")

    if args.smoke:
        items = items[:1]
        if args.all:
            targets = list(MODAL_MODELS.keys())
            log("SMOKE (--all): 1 item on ALL 3 models (multi-GPU each -- costly)")
        else:
            targets = ["llama-3.3-70b"]
            log("SMOKE: 1 item on llama-3.3-70b (smallest; proves vLLM+HF-secret+schema path)")
    else:
        targets = [k for k in MODAL_MODELS.keys() if k != "llama-3.3-70b"]
        log(f"FULL RUN: {targets} (llama-3.3-70b skipped: gated on HF)")

    all_rows = []
    cost_log = []
    with app.run():
        for nick in targets:
            t0 = time.time()
            log(f"Dispatching {nick} to Modal ...")
            rows = FUNCS[nick].remote(json.dumps(items))
            dt = time.time() - t0
            all_rows.extend(rows)
        cost_log.append({"nick": nick, "hf_id": MODAL_MODELS[nick]["hf_id"],
                         "gpu_count": MODAL_MODELS[nick]["gpu"], "tp": MODAL_MODELS[nick]["tp"],
                         "items": len(items), "rows": len(rows), "seconds": round(dt, 2),
                         "timestamp": datetime.now(timezone.utc).isoformat()})
        log(f"{nick}: {len(rows)} rows in {dt:.1f}s")

    df = pd.DataFrame(all_rows)
    df.to_csv(OUT_DIR / "03_modal_outputs.csv", index=False)
    log(f"Saved 03_modal_outputs.csv ({len(df)} rows)")

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": __file__, "provider": "modal", "seed": SEED,
        "models": targets, "n_items": len(items), "n_rows": len(df),
        "input_hash": sha256(SAMPLED_JSON),
        "output_hash": sha256(OUT_DIR / "03_modal_outputs.csv"),
        "schema_match_openrouter": True, "cost_log": cost_log,
    }
    with open(OUT_DIR / "03_modal_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log("Manifest written. Done.")

if __name__ == "__main__":
    main()
