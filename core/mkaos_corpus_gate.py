"""Separate permission to train from permission to redistribute model weights.

Training on a reviewed source does not automatically grant rights to publish
checkpoint weights. A source may be approved for private/non-redistributable
training while weight_distribution_review remains pending or not approved.
"""
from __future__ import annotations

from typing import Any


def validate_source_registry(manifest: Any, registry: Any) -> list[str]:
    """Require source approval for training; independently gate weight distribution."""
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
        scope = source.get("training_scope")
        if scope not in {"internal_nonredistributable", "redistributable"}:
            errors.append(
                f"Source {source_id!r} needs training_scope='internal_nonredistributable' "
                "or 'redistributable'."
            )
        if scope == "redistributable" and source.get("weight_distribution_review") != "approved":
            errors.append(
                f"Source {source_id!r} claims redistributable training but has no approved "
                "model-weight distribution review."
            )
        if scope == "internal_nonredistributable" and source.get("weight_distribution_review") == "approved":
            # Not unsafe, but contradictory metadata often causes accidental publication.
            if source.get("redistribution_permission") is False:
                errors.append(
                    f"Source {source_id!r} contradicts internal_nonredistributable scope "
                    "with redistribution_permission=false and approved weight distribution."
                )
    if errors:
        return errors
    scopes = {
        by_id[source_id].get("training_scope")
        for source_id in used_ids
        if source_id in by_id
    }
    if scopes == {"internal_nonredistributable"}:
        return [
            "Source register checks passed for internal non-redistributable training only; "
            "checkpoint publication remains blocked until weight distribution is separately approved."
        ]
    return [
        "Source register checks passed; redistributable weights are permitted only for sources "
        "whose weight_distribution_review is explicitly approved. This does not replace independent "
        "legal, privacy, or quality review."
    ]


def validate_experimental_local_manifest(manifest: Any, registry: Any) -> list[str]:
    """Allow an owner-authorized, local-only experiment without claiming source clearance.

    This path is intentionally separate from production/distribution approval. It
    requires an explicit CLI opt-in and a manifest that declares the data is
    owner-created or separately rights-cleared, local-only, and non-redistributable.
    """
    if not isinstance(manifest, dict):
        return ["Experimental manifest must be a JSON object."]
    if not isinstance(registry, dict):
        return ["Source register must be a JSON object."]
    authorization = registry.get("project_owner_authorization")
    if not isinstance(authorization, dict) or authorization.get("status") != "granted_by_project_owner_in_chat":
        return ["Experimental local training requires recorded project-owner authorization."]
    if manifest.get("data_rights_mode") != "owner_supplied_local_nonredistributable":
        return [
            "Experimental mode requires manifest data_rights_mode="
            "'owner_supplied_local_nonredistributable'."
        ]
    if manifest.get("source_kind") != "owner_created_or_rights_cleared_local":
        return [
            "Experimental mode requires source_kind="
            "'owner_created_or_rights_cleared_local'; third-party candidate datasets are not accepted."
        ]
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        return ["Experimental manifest must contain records."]
    for index, row in enumerate(records):
        if not isinstance(row, dict) or not isinstance(row.get("source_id"), str) or not row["source_id"].strip():
            return [f"Experimental manifest records[{index}] needs a non-empty source_id."]
    return [
        "Experimental local-only gate passed. This does NOT clear third-party rights, "
        "PII/privacy, or model-weight redistribution; the resulting checkpoint must not be distributed."
    ]
