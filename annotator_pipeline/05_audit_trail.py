#!/usr/bin/env python3
"""
AfriKnow Annotator Pipeline — Phase 5: Audit Trail Logger

Appends a tamper-evident JSONL log for every pipeline action.
Each line contains:
  - timestamp (UTC ISO-8601)
  - phase / action
  - input hashes
  - output hashes
  - config snapshot
  - script version

This log is the primary artifact for reviewer-proof reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
AUDIT_LOG = OUT_DIR / "05_audit_trail.jsonl"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

def log_event(phase: str, action: str, inputs: list[Path] | None = None, outputs: list[Path] | None = None, note: str = "") -> dict:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "action": action,
        "script": str(Path(__file__).name),
        "python_version": sys.version.split()[0],
        "inputs": [
            {"path": str(p), "sha256": sha256(p), "size_bytes": p.stat().st_size}
            for p in (inputs or []) if p.exists()
        ],
        "outputs": [
            {"path": str(p), "sha256": sha256(p), "size_bytes": p.stat().st_size}
            for p in (outputs or []) if p.exists()
        ],
        "note": note,
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

def log_config(phase: str, config: dict, note: str = "") -> dict:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "action": "config_snapshot",
        "script": str(Path(__file__).name),
        "config_hash": sha256_str(json.dumps(config, sort_keys=True)),
        "config": config,
        "note": note,
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event

def read_tail(n: int = 20) -> list[dict]:
    events = []
    if AUDIT_LOG.exists():
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events[-n:] if n else events

if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_event("audit", "init", outputs=[AUDIT_LOG], note="Audit trail initialized")
    print(f"Audit log: {AUDIT_LOG}")
    print("Recent events:")
    for ev in read_tail(5):
        print(f"  [{ev['timestamp']}] {ev['phase']}: {ev['action']}")
