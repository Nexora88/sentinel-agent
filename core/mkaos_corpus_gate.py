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
    if any(not isinstance(source_id, str) or not source_id.strip() for source_id in approved_ids):
        errors.append("Every approved source ID must be a non-empty string.")
    if len(approved_ids) != len(set(item for item in approved_ids if isinstance(item, str))):
        errors.append("Source register contains duplicate approved source IDs.")
    sources = registry.get("sources")
    if not isinstance(sources, list):
        return errors + ["Source register must contain a sources array."]
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(sources):
        if not isinstance(item, dict) or not isinstance(item.get("source_id"), str) or not item["source_id"].strip():
            errors.append(f"Source register sources[{index}] needs a non-empty source_id.")
            continue
        source_id = item["source_id"]
        if source_id in by_id:
            errors.append(f"Source register has duplicate source_id {source_id!r}; refusing ambiguous approval.")
            errors.append(f"Source {source_id!r} is not explicitly approved because duplicate source IDs make approval ambiguous.")
            by_id.pop(source_id, None)
            continue
        by_id[source_id] = item
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["Training manifest must contain records."]
    used_ids: set[str] = set()
    for index, row in enumerate(records):
        if not isinstance(row, dict) or not isinstance(row.get("source_id"), str) or not row["source_id"].strip():
            errors.append(f"Training manifest records[{index}] needs a non-empty source_id.")
            continue
        used_ids.add(row["source_id"])
    for source_id in sorted(used_ids):
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
