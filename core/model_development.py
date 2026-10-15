"""Governed local-model development primitives for MKAOS.

This module prepares auditable datasets and evaluates candidate releases. It does
not train weights, collect data, or publish a model automatically.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


class ModelDevelopmentError(ValueError):
    """A dataset record or candidate release fails a governance requirement."""


REQUIRED_FIELDS = {"prompt", "response", "source_id", "source_uri", "license_id", "consent"}
DEFAULT_ALLOWED_LICENSES = frozenset({"CC0-1.0", "CC-BY-4.0", "MIT", "Apache-2.0"})
SENSITIVE_MARKERS = ("[REDACTED_PII]", "[REDACTED_SECRET]", "[REDACTED_HEALTH_DATA]")


def _text(value: Any, field: str, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ModelDevelopmentError(f"{field} must be a string")
    value = value.strip()
    if not value or len(value) > max_chars:
        raise ModelDevelopmentError(f"{field} must contain 1..{max_chars} characters")
    return value


def normalize_record(record: Mapping[str, Any], *,
                     allowed_licenses: Iterable[str] = DEFAULT_ALLOWED_LICENSES) -> dict[str, Any]:
    """Validate one supervised example; this is not a legal opinion or a PII detector."""
    if not isinstance(record, Mapping):
        raise ModelDevelopmentError("record must be an object")
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        raise ModelDevelopmentError("missing required fields: " + ", ".join(sorted(missing)))
    prompt = _text(record["prompt"], "prompt", 20_000)
    response = _text(record["response"], "response", 30_000)
    source_id = _text(record["source_id"], "source_id", 200)
    source_uri = _text(record["source_uri"], "source_uri", 2_000)
    license_id = _text(record["license_id"], "license_id", 100)
    if license_id not in set(allowed_licenses):
        raise ModelDevelopmentError(f"license not allowlisted: {license_id}")
    if record["consent"] is not True:
        raise ModelDevelopmentError("explicit permission/consent evidence is required")
    if record.get("personal_data") is True or record.get("sensitive_data") is True:
        raise ModelDevelopmentError("personal or sensitive data must be removed before ingestion")
    if record.get("review_status", "approved") != "approved":
        raise ModelDevelopmentError("record must pass human/data-governance review")
    if not source_uri.startswith(("https://", "file://", "dataset://")):
        raise ModelDevelopmentError("source_uri must be an auditable HTTPS or local dataset URI")
    if any(marker in prompt or marker in response for marker in SENSITIVE_MARKERS):
        raise ModelDevelopmentError("redaction markers remain; record needs review")
    canonical = {
        "prompt": prompt, "response": response, "source_id": source_id,
        "source_uri": source_uri, "license_id": license_id, "consent": True,
    }
    canonical["content_sha256"] = hashlib.sha256(
        (prompt + "\\0" + response).encode("utf-8")
    ).hexdigest()
    return canonical


def curate_dataset(records: Iterable[Mapping[str, Any]], *,
                   allowed_licenses: Iterable[str] = DEFAULT_ALLOWED_LICENSES) -> dict[str, Any]:
    """Validate, deduplicate and source-split examples to reduce train/test leakage."""
    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    rejected: list[dict[str, str]] = []
    for index, raw in enumerate(records):
        try:
            item = normalize_record(raw, allowed_licenses=allowed_licenses)
            digest = item["content_sha256"]
            if digest in seen:
                rejected.append({"index": str(index), "reason": "duplicate_content"})
                continue
            seen.add(digest)
            clean.append(item)
        except (ModelDevelopmentError, TypeError) as exc:
            rejected.append({"index": str(index), "reason": str(exc)})
    source_split: dict[str, str] = {}
    for item in clean:
        source = item["source_id"]
        bucket = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:8], 16) % 100
        source_split[source] = "train" if bucket < 80 else ("validation" if bucket < 90 else "test")
    for item in clean:
        item["split"] = source_split[item["source_id"]]
    split_counts = Counter(item["split"] for item in clean)
    manifest = json.dumps(clean, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "schema_version": "1.0", "records": clean,
        "summary": {
            "accepted": len(clean), "rejected": len(rejected),
            "split_counts": dict(split_counts), "unique_sources": len(source_split),
            "licenses": dict(Counter(item["license_id"] for item in clean)),
            "content_sha256": hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
        },
        "rejections": rejected,
        "training_allowed": len(clean) > 0 and bool(split_counts.get("train")) and bool(split_counts.get("test")),
    }


@dataclass(frozen=True)
class PromotionPolicy:
    min_test_examples: int = 100
    min_quality_score: float = 0.85
    max_quality_regression: float = 0.01
    max_latency_regression: float = 0.20


def evaluate_promotion(*, baseline: Mapping[str, Any], candidate: Mapping[str, Any],
                       test_examples: int, critical_safety_failures: int,
                       human_review_approved: bool,
                       policy: PromotionPolicy = PromotionPolicy()) -> dict[str, Any]:
    """Return a release-gate report; never deploy or mutate model weights."""
    try:
        base_quality = float(baseline["quality_score"])
        new_quality = float(candidate["quality_score"])
        base_latency = float(baseline["latency_p95_ms"])
        new_latency = float(candidate["latency_p95_ms"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ModelDevelopmentError("baseline/candidate metrics are incomplete") from exc
    issues: list[str] = []
    if test_examples < policy.min_test_examples:
        issues.append("held_out_test_set_too_small")
    if not 0 <= new_quality <= 1 or not 0 <= base_quality <= 1:
        issues.append("quality_score_out_of_range")
    if new_quality < policy.min_quality_score:
        issues.append("quality_below_minimum")
    if new_quality < base_quality - policy.max_quality_regression:
        issues.append("quality_regression")
    if base_latency <= 0 or new_latency <= 0:
        issues.append("invalid_latency_measurement")
    elif new_latency > base_latency * (1 + policy.max_latency_regression):
        issues.append("latency_regression")
    if critical_safety_failures != 0:
        issues.append("critical_safety_failure")
    if not human_review_approved:
        issues.append("human_review_required")
    return {
        "decision": "eligible_for_release_review" if not issues else "blocked",
        "issues": issues, "deploy_automatically": False,
        "requires_human_release_approval": True,
    }
