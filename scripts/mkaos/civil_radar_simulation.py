"""Toy civil radar signal-processing demo using synthetic data only.

This is an educational signal/noise/filter example, not a radar model or
operational sensor implementation. It uses no external dependencies.
"""
from __future__ import annotations

import math
import random


def generate_synthetic_echoes(
    sample_count: int = 256, seed: int = 7, noise_amplitude: float = 0.15
) -> list[float]:
    """Return a reproducible toy waveform with two synthetic echo bumps."""
    if sample_count < 16 or sample_count > 100_000:
        raise ValueError("sample_count must be between 16 and 100000")
    if not math.isfinite(noise_amplitude) or not 0 <= noise_amplitude <= 1:
        raise ValueError("noise_amplitude must be finite and between 0 and 1")

    rng = random.Random(seed)
    values: list[float] = []
    for i in range(sample_count):
        background = rng.uniform(-noise_amplitude, noise_amplitude)
        echo_a = 0.8 * math.exp(-((i - sample_count * 0.32) / 5.0) ** 2)
        echo_b = 0.55 * math.exp(-((i - sample_count * 0.70) / 8.0) ** 2)
        values.append(background + echo_a + echo_b)
    return values


def moving_average(values: list[float], window: int = 5) -> list[float]:
    """Apply a centered moving average while preserving output length."""
    if not values:
        return []
    if window < 1 or window > len(values):
        raise ValueError("window must be between 1 and the input length")
    left = (window - 1) // 2
    right = window // 2
    result: list[float] = []
    for i in range(len(values)):
        start = max(0, i - left)
        end = min(len(values), i + right + 1)
        result.append(sum(values[start:end]) / (end - start))
    return result


def summarize_signal(values: list[float]) -> dict[str, float | int]:
    """Return simple descriptive statistics; not a detection decision."""
    if not values:
        raise ValueError("values must not be empty")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("values must be finite")
    return {
        "sample_count": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": sum(values) / len(values),
    }


if __name__ == "__main__":
    raw = generate_synthetic_echoes()
    filtered = moving_average(raw)
    print({"raw": summarize_signal(raw), "filtered": summarize_signal(filtered)})
