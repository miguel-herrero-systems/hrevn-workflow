from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from .hashing import file_metadata


def build_deliverables_from_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_by_path: dict[str, dict[str, Any]] = {}
    for step in steps:
        for output in step.get("outputs", []):
            path = output.get("path")
            if not path:
                continue
            latest_by_path[path] = {
                "path": path,
                "sha256": output.get("sha256"),
                "role": "workflow_output",
            }
    return list(latest_by_path.values())


def build_verified_record_payload(
    manifest_path: Path,
    manifest: dict[str, Any],
    case_reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = file_metadata(manifest_path)
    base_reference = {
        "workflow_id": manifest.get("workflow_id"),
        "run_id": manifest.get("run_id"),
        "project": manifest.get("project"),
    }
    if case_reference:
        base_reference.update(case_reference)

    certified_deliverables = [
        {
            "document_id": "workflow_manifest",
            "role": "workflow_manifest",
            "type": "application/json",
            "filename": manifest_path.name,
            "sha256": metadata["sha256"],
            "size_bytes": metadata["size_bytes"],
            "generated_at": manifest.get("exported_at"),
            "delivery_status": "local",
            "included_in_zip": False,
        }
    ]

    for index, deliverable in enumerate(manifest.get("certifiable_deliverables", []), start=1):
        path = deliverable.get("path")
        if not path:
            continue
        deliverable_path = Path(path)
        current_metadata = file_metadata(deliverable_path)
        mime_type, _ = mimetypes.guess_type(deliverable_path.name)
        certified_deliverables.append(
            {
                "document_id": f"workflow_output_{index}",
                "role": deliverable.get("role", "workflow_output"),
                "type": mime_type or "application/octet-stream",
                "filename": deliverable_path.name,
                "sha256": current_metadata["sha256"],
                "size_bytes": current_metadata["size_bytes"],
                "generated_at": manifest.get("exported_at"),
                "delivery_status": "local",
                "included_in_zip": False,
            }
        )

    return {
        "integration_profile": "hrevn_workflow_verified_state_v0.1",
        "case_reference": base_reference,
        "certified_deliverables": certified_deliverables,
        "workflow_summary": {
            "steps_count": manifest.get("steps_count", 0),
            "completed_steps": manifest.get("completed_steps", 0),
            "failed_steps": manifest.get("failed_steps", 0),
            "last_valid_step": manifest.get("last_valid_step"),
        },
    }
