"""Fail-closed source registry gate for MKAOS training."""
from __future__ import annotations

from typing import Any


def validate_source_registry(manifest: Any, registry: Any) -> list[str]:
    """Require explicit source-level approval before any checkpoint training."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["Training manifest must be a JSON object."]
    if not isinstance(registry, dict):
        return ["Source register must be a JSON object."]
    if registry.get("model_training_allowed") is not True:
        errors.append("Source register does not authorize model training.")
    approved_ids = registry.get("current_approved_sources")
    if not isinstance(approved_ids, list) or not approved_ids:
        errors.append("Source register has no explicitly approved source IDs.")
        approved_ids = []
    sources = registry.get("sources")
    if not isinstance(sources, list):
        return errors + ["Source register must contain a sources array."]
    by_id = {
        item.get("source_id"): item
        for item in sources
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["Training manifest must contain records."]
    used_ids = {row.get("source_id") for row in records if isinstance(row, dict)}
    for source_id in sorted(used_ids, key=str):
        source = by_id.get(source_id)
        if source is None:
            errors.append(f"Source {source_id!r} is absent from the source register.")
            continue
        if source_id not in approved_ids:
            errors.append(f"Source {source_id!r} is not in current_approved_sources.")
        if source.get("status") != "approved" or source.get("permitted_use_now") is not True:
            errors.append(f"Source {source_id!r} is not explicitly approved for current use.")
        if not isinstance(source.get("approved_revision"), str) or not source["approved_revision"].strip():
            errors.append(f"Source {source_id!r} has no pinned approved_revision.")
        if not isinstance(source.get("approval_evidence"), str) or not source["approval_evidence"].strip():
            errors.append(f"Source {source_id!r} has no approval_evidence reference.")
        if source.get("weight_distribution_review") != "approved":
            errors.append(f"Source {source_id!r} has no approval for model-weight distribution.")
    if errors:
        return errors
    return ["Source register checks passed; this does not replace independent legal, privacy, or quality review."]
