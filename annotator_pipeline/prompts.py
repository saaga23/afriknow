"""Shared prompt builders, parsers, and extractors for AfriKnow annotator pipeline.

All runners MUST import from this module to ensure consistency across
OpenRouter, Modal, pilot, and full-run lanes.
"""

from __future__ import annotations

import re


def build_mcqa_prompt(item: dict) -> str:
    lines = [
        "Answer the following multiple-choice question with ONLY the letter of the correct answer (A, B, C, or D). No explanation is needed.",
        "",
        item["q"],
    ]
    for i, c in enumerate(item["ch"]):
        lines.append(f"{chr(65 + i)}. {c}")
    lines.extend(["", "Answer:"])
    return "\n".join(lines)


def build_vce_prompt(item: dict, predicted_letter: str) -> str:
    lines = [
        "You already selected an answer for the question below.",
        "Now provide ONLY your confidence in that answer as an integer from 0 to 100.",
        "No explanation is needed; output just the number.",
        "",
        item["q"],
    ]
    for i, c in enumerate(item["ch"]):
        lines.append(f"{chr(65 + i)}. {c}")
    lines.extend([
        "",
        f"Your selected answer: {predicted_letter}",
        "",
        "Confidence (0-100):",
    ])
    return "\n".join(lines)


def clean_raw_text(text: str, purpose: str = "greedy") -> str:
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


def parse_letter(text: str | None) -> str:
    if text is None:
        return "X"
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.DOTALL)
    for pat in [
        r"the best answer is\s+([A-D])",
        r"the correct answer is\s+([A-D])",
        r"final answer\s*[:=]?\s*([A-D])",
        r"answer\s*[:=]\s+([A-D])",
        r"answer is\s+([A-D])",
    ]:
        m = re.findall(pat, text, re.IGNORECASE)
        if m:
            return m[-1].upper()
    m = re.search(r"\b([A-D])\b", text)
    if m:
        return m.group(1).upper()
    return "X"


def extract_conf(text: str | None) -> float:
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


def get_gold_letter(item: dict) -> str:
    """Unified gold-label extraction. Handles both 'answer' (letter) and 'a' (index)."""
    if "answer" in item and isinstance(item["answer"], str):
        return item["answer"].strip().upper()
    gold_idx = item.get("a", 0)
    try:
        return chr(65 + int(gold_idx))
    except (TypeError, ValueError):
        return "A"
