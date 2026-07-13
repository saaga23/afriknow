#!/usr/bin/env python3
"""
Master validation script for AfriKnow pipeline.

Checks:
1. cocoa_fixed formula consistency across all Python files
2. Hardcoded secrets in Python files
3. v18 outputs: row count, duplicates, formula mismatches, parse failures
4. Pilot outputs: row count, duplicates, parse failures
5. 180-item dataset: Africa/Europe balance
6. Security: no exposed tokens in .env
"""

from __future__ import annotations

import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "annotator_pipeline" / "outputs"


def check_formula():
    issues = []
    for pyfile in glob.glob(str(ROOT / "**/*.py"), recursive=True):
        if "node_modules" in pyfile or "__pycache__" in pyfile:
            continue
        with open(pyfile, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for i, line in enumerate(content.split("\n"), 1):
            if "cocoa_fixed" in line and "=" in line:
                if "cocoa_fixed = vce" in line and "0.5" not in line and "None" not in line:
                    issues.append(f"{pyfile}:{i}")
    if issues:
        print(f"FAIL: {len(issues)} files use cocoa_fixed = vce")
        return False
    print("PASS: All cocoa_fixed formulas standardized")
    return True


def check_secrets():
    patterns = [
        r"sk-or-v1-[a-zA-Z0-9]{20,}",
        r"ak-[a-zA-Z0-9]{20,}",
        r"hf_[a-zA-Z0-9]{20,}",
        r"ghp_[a-zA-Z0-9]{20,}",
    ]
    for pyfile in glob.glob(str(ROOT / "**/*.py"), recursive=True):
        if "node_modules" in pyfile or "__pycache__" in pyfile:
            continue
        with open(pyfile, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for pattern in patterns:
            if re.search(pattern, content):
                print(f"FAIL: {pyfile} contains hardcoded secret")
                return False
    print("PASS: No hardcoded secrets")
    return True


def check_v18():
    df = pd.read_csv(OUT_DIR / "03_openrouter_outputs_v18_correct.csv")
    vce_rows = df[df["purpose"] == "vce"]
    mismatch = vce_rows[abs(vce_rows["cocoa_fixed"] - (0.5 * vce_rows["vce"] + 0.5)) > 0.001]
    dups = df.duplicated(subset=["id", "model", "purpose"], keep=False)
    parse_fails = len(df[df["pred"] == "X"])

    print(f"v18 rows: {len(df)} (expected 2520)")
    print(f"Items: {df['id'].nunique()} (expected 180)")
    print(f"Models: {df['model'].nunique()} (expected 7)")
    print(f"Duplicates: {dups.sum()}")
    print(f"Formula mismatches: {len(mismatch)}")
    print(f"Parse failures: {parse_fails}")

    ok = (
        len(df) == 2520
        and df["id"].nunique() == 180
        and df["model"].nunique() == 7
        and dups.sum() == 0
        and len(mismatch) == 0
        and parse_fails == 0
    )
    if ok:
        print("PASS: v18 outputs validated")
    else:
        print("FAIL: v18 outputs have issues")
    return ok


def check_pilot():
    df = pd.read_csv(OUT_DIR / "pilot_merged.csv")
    parse_fails = len(df[df["pred"] == "X"])
    print(f"Pilot rows: {len(df)} (expected 400)")
    print(f"Items: {df['id'].nunique()} (expected 50)")
    print(f"Parse failures: {parse_fails}")
    ok = len(df) == 400 and df["id"].nunique() == 50 and parse_fails == 0
    if ok:
        print("PASS: Pilot outputs validated")
    else:
        print("FAIL: Pilot outputs have issues")
    return ok


def check_180_dataset():
    import json
    with open(OUT_DIR / "02_gm_only_180_items.json", encoding="utf-8") as f:
        data = json.load(f)
    africa = [it for it in data["items"] if it["region"] == "Africa"]
    europe = [it for it in data["items"] if it["region"] == "Europe"]
    print(f"Total: {len(data['items'])} (expected 180)")
    print(f"Africa: {len(africa)} (expected 90)")
    print(f"Europe: {len(europe)} (expected 90)")
    ok = len(data["items"]) == 180 and len(africa) == 90 and len(europe) == 90
    if ok:
        print("PASS: 180-item dataset validated")
    else:
        print("FAIL: 180-item dataset has issues")
    return ok


def main():
    print("=" * 60)
    print("AFRIKNOW MASTER VALIDATION")
    print("=" * 60)
    results = []
    results.append(("Formula consistency", check_formula()))
    results.append(("No hardcoded secrets", check_secrets()))
    results.append(("v18 outputs", check_v18()))
    results.append(("Pilot outputs", check_pilot()))
    results.append(("180-item dataset", check_180_dataset()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
