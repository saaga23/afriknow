#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Orchestrator

Runs analysis phases in sequence with a tamper-evident audit trail.
Every phase is logged with input/output SHA256 hashes and a config snapshot.

Usage:
  python run_pipeline.py --analysis

Phases:
   01 power analysis
   02 stratified sample design
   03 Kaggle inference (manual via website or CLI)
   04 analysis (7-model accuracy, calibration, mixed-effects)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs"
AUDIT_LOG = OUT_DIR / "05_audit_trail.jsonl"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def log_event(phase, action, inputs=None, outputs=None, note=""):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "action": action,
        "orchestrator": "run_pipeline.py",
        "inputs": [{"path": str(p), "sha256": sha256(p), "size": p.stat().st_size} for p in (inputs or []) if p.exists()],
        "outputs": [{"path": str(p), "sha256": sha256(p), "size": p.stat().st_size} for p in (outputs or []) if p.exists()],
        "note": note,
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

def run_phase(script_name: str, phase_label: str, extra_args=None, expect_outputs=None):
    print(f"\n{'='*70}\n  PHASE {phase_label}: {script_name}\n{'='*70}")
    cmd = [sys.executable, str(ROOT / script_name)] + (extra_args or [])
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=False)
    if result.returncode != 0:
        print(f"[FATAL] Phase {phase_label} failed with code {result.returncode}")
        log_event(phase_label, "FAILED", outputs=expect_outputs, note=f"returncode={result.returncode}")
        raise SystemExit(result.returncode)
    print(f"[OK] Phase {phase_label} completed")
    return result

def main():
    parser = argparse.ArgumentParser(description="AfriKnow annotator pipeline orchestrator")
    parser.add_argument("--analysis", action="store_true", help="run analysis phases only")
    parser.add_argument("--only", type=str, default=None, help="run only one phase: 01, 02, 03, 04")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    config = {
        "seed": 42,
        "n_per_region": 90,
        "total_items": 180,
        "exclude_flagged": True,
        "models_openrouter": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "deepseek/deepseek-v3.2",
            "qwen/qwen3-235b-a22b-2507",
            "meta-llama/llama-3.3-70b-instruct",
            "openai/gpt-4.1-nano",
            "google/gemini-2.5-flash-lite",
        ],
        "confidence_signals": ["greedy", "vce"],
        "budget_cap_usd": 0.5,
        "python": sys.version.split()[0],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    log_event("config", "snapshot", note=json.dumps(config, sort_keys=True))

    phases = []
    if not args.analysis:
        phases.extend([
            ("01_power_analysis.py", "01", None, [OUT_DIR / "01_power_analysis_report.md"]),
            ("02_sample_design.py", "02", None, [OUT_DIR / "02_sampled_items.json"]),
        ])

    phases.extend([
        ("analyze_kaggle_7model.py", "03", None, [OUT_DIR / "kaggle_8model_outputs.csv"]),
        ("reanalyze_mixed_effects.py", "04", None, [OUT_DIR / "mixed_effects_results.md"]),
    ])

    for script_name, label, extra, expect in phases:
        if args.only and args.only != label:
            continue
        run_phase(script_name, label, extra_args=extra, expect_outputs=expect)
        log_event(label, "completed", outputs=expect, note=f"script={script_name}")

    print(f"\n{'='*70}\n  PIPELINE COMPLETE\n  Audit trail: {AUDIT_LOG}\n{'='*70}")
    print(f"  Audit events: {sum(1 for _ in open(AUDIT_LOG, encoding='utf-8') if _.strip())}")

if __name__ == "__main__":
    main()
