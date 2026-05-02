from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from .config import CertificationSettings


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class CertificationResult:
    ok: bool
    status: str
    certified_at: str | None = None
    bundle_id: str | None = None
    record_id: str | None = None
    download_url: str | None = None
    expires_at: str | None = None
    error: str | None = None
    request_summary: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "ok": self.ok,
            "status": self.status,
            "certified_at": self.certified_at,
            "bundle_id": self.bundle_id,
            "record_id": self.record_id,
            "download_url": self.download_url,
            "expires_at": self.expires_at,
            "error": self.error,
            "request_summary": self.request_summary or {},
        }
        if self.response_payload is not None:
            payload["response_payload"] = self.response_payload
        return payload


def build_generate_bundle_request(
    *,
    workflow_id: str,
    run_id: str,
    project: str | None,
    manifest_path: Path,
    verified_record_payload: dict[str, Any],
    settings: CertificationSettings,
) -> dict[str, Any]:
    case_reference = dict(verified_record_payload.get("case_reference", {}))
    case_reference.setdefault("workflow_id", workflow_id)
    case_reference.setdefault("run_id", run_id)
    if project:
        case_reference.setdefault("project", project)
    case_reference.setdefault("product", "workflow_sdk")
    case_reference.setdefault("title", f"Workflow certification for {workflow_id}")
    case_reference.setdefault("description", "Local workflow manifest and deliverables certified through HREVN.")

    record = {
        "agent_name": settings.agent_name,
        "model_version": settings.model_version,
        "task_description": f"Certify workflow manifest for {workflow_id}",
        "test_environment": settings.test_environment,
        "issuer_id": settings.issuer_id,
        "issuer_name": settings.issuer_name,
        "issuer_type": settings.issuer_type,
        "distribution_channel": settings.distribution_channel,
        "delivery_mode": settings.delivery_mode,
        "integration_profile": verified_record_payload.get(
            "integration_profile", "hrevn_workflow_verified_state_v0.1"
        ),
        "case_reference": case_reference,
        "certified_deliverables": verified_record_payload.get("certified_deliverables", []),
    }
    if settings.license_id:
        record["license_id"] = settings.license_id
    if settings.installation_id:
        record["installation_id"] = settings.installation_id

    return {
        "record": record,
        "traces": [
            {
                "test_id": "WF-CERT-001",
                "result": "PASS",
                "confidence": "high",
                "duration_ms": 0,
                "tokens_used": 0,
                "input_text": str(manifest_path),
                "validator_notes": ["Workflow manifest prepared and validated locally before certification."],
            }
        ],
    }


def submit_generate_bundle(api_base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = api_base_url.rstrip("/") + "/v1/generate-bundle"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = urllib_request.Request(
        endpoint,
        data=raw,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib_request.urlopen(http_request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def certify_manifest(
    *,
    workflow_id: str,
    run_id: str,
    project: str | None,
    manifest_path: Path,
    verified_record_payload: dict[str, Any],
    settings: CertificationSettings,
) -> CertificationResult:
    if settings.mode == "disabled":
        return CertificationResult(
            ok=False,
            status="disabled",
            error="Certification disabled by HREVN_WORKFLOW_CERTIFY_MODE=disabled.",
            request_summary={"workflow_id": workflow_id, "run_id": run_id},
        )

    if not settings.api_base_url or not settings.api_key:
        return CertificationResult(
            ok=False,
            status="not_configured",
            error="Missing HREVN_API_BASE_URL or HREVN_API_KEY for integrated certification.",
            request_summary={"workflow_id": workflow_id, "run_id": run_id},
        )

    payload = build_generate_bundle_request(
        workflow_id=workflow_id,
        run_id=run_id,
        project=project,
        manifest_path=manifest_path,
        verified_record_payload=verified_record_payload,
        settings=settings,
    )

    try:
        response_payload = submit_generate_bundle(settings.api_base_url, settings.api_key, payload)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return CertificationResult(
            ok=False,
            status="failed",
            error=f"HTTP {exc.code}: {detail}",
            request_summary={"workflow_id": workflow_id, "run_id": run_id, "manifest_path": str(manifest_path)},
        )
    except URLError as exc:
        return CertificationResult(
            ok=False,
            status="failed",
            error=f"Network error during certification: {exc}",
            request_summary={"workflow_id": workflow_id, "run_id": run_id, "manifest_path": str(manifest_path)},
        )

    return CertificationResult(
        ok=True,
        status="generated",
        certified_at=utc_now(),
        bundle_id=response_payload.get("bundle_id"),
        record_id=(response_payload.get("metadata") or {}).get("record_id"),
        download_url=response_payload.get("download_url"),
        expires_at=response_payload.get("expires_at"),
        request_summary={"workflow_id": workflow_id, "run_id": run_id, "manifest_path": str(manifest_path)},
        response_payload=response_payload,
    )
