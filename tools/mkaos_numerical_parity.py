"""Numerical parity metrics for reference-vs-candidate model outputs.

This utility compares caller-supplied flattened logits; it does not load models,
convert weights, or claim that any adapter is compatible by itself.
"""
from __future__ import annotations
import math
from typing import Iterable

def compare_vectors(reference: Iterable[float], candidate: Iterable[float], *, atol: float = 1e-5, rtol: float = 1e-4) -> dict:
    ref = [float(x) for x in reference]
    got = [float(x) for x in candidate]
    if not ref or len(ref) != len(got):
        raise ValueError("vectors must be non-empty and have equal lengths")
    if any(not math.isfinite(x) for x in ref + got):
        raise ValueError("vectors must contain only finite numbers")
    if atol < 0 or rtol < 0:
        raise ValueError("tolerances must be non-negative")
    diffs = [abs(a - b) for a, b in zip(ref, got)]
    max_abs = max(diffs)
    max_rel = max(d / max(abs(a), 1e-12) for d, a in zip(diffs, ref))
    dot = sum(a * b for a, b in zip(ref, got))
    norm_ref = math.sqrt(sum(a * a for a in ref))
    norm_got = math.sqrt(sum(b * b for b in got))
    cosine = dot / (norm_ref * norm_got) if norm_ref and norm_got else (1.0 if norm_ref == norm_got == 0 else 0.0)
    passed = all(d <= atol + rtol * abs(a) for d, a in zip(diffs, ref))
    return {"elements": len(ref), "max_absolute_error": max_abs, "max_relative_error": max_rel,
            "cosine_similarity": cosine, "atol": atol, "rtol": rtol, "passed": passed}
