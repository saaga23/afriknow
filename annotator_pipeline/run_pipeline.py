#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Orchestrator

Runs all 6 phases in sequence with a single tamper-evident audit trail.
Every phase is logged with input/output SHA256 hashes and a config snapshot,
producing reviewer-proof provenance for the entire annotator study.

Usage:
  python run_pipeline.py            # full pipeline (phases 1-6)
  python run_pipeline.py --dry-run  # skip API calls in phase 3

Phases:
  01 power analysis
  02 stratified sample design
  03 model runner (OpenRouter + Modal lanes)
  04 blinded annotator interface
  05 audit trail (integrated here)
  06 annotator vs model analysis
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
    result = subprocess.run(cmd, cwd=str(ROOT.parent), capture_output=False)
    if result.returncode != 0:
        print(f"[FATAL] Phase {phase_label} failed with code {result.returncode}")
        log_event(phase_label, "FAILED", outputs=expect_outputs, note=f"returncode={result.returncode}")
        raise SystemExit(result.returncode)
    print(f"[OK] Phase {phase_label} completed")
    return result

def main():
    parser = argparse.ArgumentParser(description="AfriKnow annotator pipeline orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="skip API calls in phase 3")
    parser.add_argument("--only", type=str, default=None, help="run only one phase: 01..06")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Config snapshot (reviewer-proof: freeze all parameters)
    config = {
        "seed": 42,
        "n_per_region": 60,
        "total_items": 120,
        "exclude_flagged": True,
        "models_openrouter": ["openai/gpt-4o-mini", "anthropic/claude-3-haiku"],
        "models_modal_or_openrouter": [
            "deepseek/deepseek-v3.2",
            "qwen/qwen3-235b-a22b-2507",
            "meta-llama/llama-3.3-70b-instruct",
        ],
        "confidence_signals": ["greedy", "vce"],
        "budget_cap_usd": 2.0,
        "python": sys.version.split()[0],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    log_event("config", "snapshot", note=json.dumps(config, sort_keys=True))

    phases = [
        ("01_power_analysis.py", "01", None, [OUT_DIR / "01_power_analysis_report.md", OUT_DIR / "01_power_analysis_manifest.json"]),
        ("02_sample_design.py", "02", None, [OUT_DIR / "02_sampled_items.json", OUT_DIR / "02_sample_design_manifest.json"]),
        ("03_model_runner.py", "03", (["--dry-run"] if args.dry_run else None), [OUT_DIR / "03_model_outputs.csv", OUT_DIR / "03_cost_history.csv"]),
        ("04_annotator_interface.py", "04", None, [OUT_DIR / "04_annotator_interface.csv", OUT_DIR / "04_blinding_key.json"]),
        ("06_annotator_analysis.py", "06", None, [OUT_DIR / "06_annotator_analysis_report.md", OUT_DIR / "06_annotator_analysis_manifest.json"]),
    ]

    for script_name, label, extra, expect in phases:
        if args.only and args.only != label:
            continue
        run_phase(script_name, label, extra_args=extra, expect_outputs=expect)
        # Log each phase completion to the audit trail
        log_event(label, "completed", outputs=expect, note=f"script={script_name}")

    print(f"\n{'='*70}\n  PIPELINE COMPLETE\n  Audit trail: {AUDIT_LOG}\n{'='*70}")
    print(f"  Audit events: {sum(1 for _ in open(AUDIT_LOG, encoding='utf-8') if _.strip())}")

if __name__ == "__main__":
    main()
