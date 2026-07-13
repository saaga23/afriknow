#!/usr/bin/env python3
"""Canonical schema for AfriKnow annotator pipeline outputs."""

REQUIRED_COLUMNS = [
    "item_idx",
    "id",
    "qid",
    "region",
    "model",
    "model_id",
    "model_class",
    "correct_letter",
    "cat",
    "diff",
    "source",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "timestamp",
    "purpose",
    "pred",
    "correct",
    "vce",
    "sc_agree",
    "cocoa_fixed",
    "greedy_text",
    "provider",
]

PURPOSE_VALUES = {"greedy", "vce"}
MODEL_CLASS_VALUES = {"closed", "open"}
PURPOSE_NULLABLE = {"vce", "greedy"}


def validate_df(df):
    """Validate that a DataFrame matches the canonical schema."""
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    extra = set(df.columns) - set(REQUIRED_COLUMNS)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if extra:
        raise ValueError(f"Unexpected extra columns: {extra}")
    invalid_purpose = set(df["purpose"].unique()) - PURPOSE_VALUES
    if invalid_purpose:
        raise ValueError(f"Invalid purpose values: {invalid_purpose}")
    invalid_class = set(df["model_class"].unique()) - MODEL_CLASS_VALUES
    if invalid_class:
        raise ValueError(f"Invalid model_class values: {invalid_class}")
    return True
