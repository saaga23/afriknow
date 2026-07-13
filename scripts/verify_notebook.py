#!/usr/bin/env python3
"""Verify Kaggle notebook structure."""

import json
from pathlib import Path

nb_path = Path(__file__).resolve().parent.parent / "kaggle_upload_notebook" / "afriknow-phase-4b-v18-post-hoc-analysis.ipynb"

with open(nb_path) as f:
    nb = json.load(f)

print(f"Notebook cells: {len(nb['cells'])}")
for i, cell in enumerate(nb['cells']):
    cell_type = cell['cell_type']
    source = ''.join(cell['source'])
    lines = source.split('\n')
    print(f"Cell {i+1}: {cell_type} ({len(lines)} lines)")
    if cell_type == 'code':
        first_line = lines[0] if lines else ""
        print(f"  First line: {first_line[:80]}")
