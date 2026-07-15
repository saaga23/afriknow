#!/usr/bin/env python3
"""
Run OpenRouter lane on mixed-source contrast items.

Atomically swaps the input file, runs 03_openrouter_runner.py,
then restores the original file.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"
MIXED_JSON = OUT_DIR / "02_mixed_source_180_items.json"
TARGET_JSON = OUT_DIR / "02_sampled_items.json"
BACKUP_JSON = OUT_DIR / "02_sampled_items.json.bak"
RUNNER = ROOT / "annotator_pipeline" / "03_openrouter_runner.py"


def atomic_replace(src: Path, dst: Path) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(dst.parent), prefix=".tmp_replace_")
    os.close(fd)
    tmp_path = Path(tmp)
    shutil.copy2(src, tmp_path)
    os.replace(str(tmp_path), str(dst))


def main():
    if not MIXED_JSON.exists():
        print(f"ERROR: {MIXED_JSON} not found. Run build_mixed_source_items.py first.")
        sys.exit(1)

    if TARGET_JSON.exists():
        shutil.copy2(TARGET_JSON, BACKUP_JSON)

    try:
        atomic_replace(MIXED_JSON, TARGET_JSON)
        cmd = [sys.executable, str(RUNNER)]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        print(result.stdout[-2000:] if result.stdout else "No stdout")
        if result.stderr:
            print("STDERR:", result.stderr[-1000:])
        if result.returncode != 0:
            print(f"Runner failed with code {result.returncode}")
            sys.exit(1)
    finally:
        if BACKUP_JSON.exists():
            atomic_replace(BACKUP_JSON, TARGET_JSON)
            BACKUP_JSON.unlink()
        elif TARGET_JSON.exists():
            TARGET_JSON.unlink()


if __name__ == "__main__":
    main()
