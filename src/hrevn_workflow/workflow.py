from __future__ import annotations

import mimetypes
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .certification import certify_manifest
from .checkpoint import Step
from .config import load_certification_settings
from .errors import WorkflowIntegrityError
from .hashing import checkpoint_hash, file_metadata
from .manifest import build_deliverables_from_steps, build_verified_record_payload
from .storage import WorkflowStorage


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Workflow:
    @classmethod
    def from_storage(cls, storage_path: str = "./.hrevn") -> "Workflow":
        storage = WorkflowStorage(storage_path)
        state = storage.load_state()
        if state is None:
            raise FileNotFoundError(f"No workflow_state.json found under {storage.root}")
        return cls(
            workflow_id=state["workflow_id"],
            storage_path=str(storage.root),
            run_id=state.get("run_id"),
            project=state.get("project"),
        )

    def __init__(
        self,
        workflow_id: str,
        storage_path: str = "./.hrevn",
        run_id: str | None = None,
        project: str | None = None,
    ) -> None:
        self.workflow_id = workflow_id
        self.project = project
        self.storage = WorkflowStorage(storage_path)
        existing_state = self.storage.load_state()
        self._state = existing_state or self._new_state(run_id=run_id)
        if run_id and self._state["run_id"] != run_id:
            self._state["run_id"] = run_id
        self.run_id = self._state["run_id"]
        self._save_state()
        if existing_state is None:
            self._track_event("workflow_initialized", storage_path=str(self.storage.root))

    def _new_state(self, run_id: str | None = None) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "run_id": run_id or f"RUN-{uuid4().hex[:12].upper()}",
            "project": self.project,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "steps": [],
        }

    def _save_state(self) -> None:
        self._state["updated_at"] = utc_now()
        self.storage.save_state(self._state)

    def _track_event(self, event_type: str, **fields: Any) -> None:
        payload = {
            "schema_version": "HREVN_WORKFLOW_TELEMETRY_v0.1",
            "event_type": event_type,
            "recorded_at": utc_now(),
            "installation_id": self.storage.load_or_create_installation_id(),
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "project": self.project,
        }
        payload.update({key: value for key, value in fields.items() if value is not None})
        self.storage.append_telemetry_event(payload)

    def _step_order(self) -> list[dict[str, Any]]:
        return list(self._state.get("steps", []))

    def _upsert_step_state(self, step_id: str, status: str, checkpoint_hash_value: str | None) -> None:
        steps = self._state.setdefault("steps", [])
        for step in steps:
            if step["step_id"] == step_id:
                step["status"] = status
                step["checkpoint_hash"] = checkpoint_hash_value
                self._save_state()
                return
        steps.append({"step_id": step_id, "status": status, "checkpoint_hash": checkpoint_hash_value})
        self._save_state()

    def step(self, step_id: str, inputs: list[str] | None = None, metadata: dict | None = None) -> Step:
        return Step(self, step_id=step_id, input_paths=inputs or [], metadata=metadata)

    def previous_completed_hash(self, exclude_step_id: str | None = None) -> str | None:
        for step in reversed(self._step_order()):
            if exclude_step_id and step["step_id"] == exclude_step_id:
                continue
            if step.get("status") == "completed":
                checkpoint = self.storage.load_checkpoint(step["step_id"])
                if checkpoint:
                    return checkpoint.get("checkpoint_hash")
        return None

    def status(self) -> dict[str, Any]:
        steps = self._step_order()
        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "project": self.project,
            "steps_count": len(steps),
            "completed_steps": sum(1 for step in steps if step["status"] == "completed"),
            "failed_steps": sum(1 for step in steps if step["status"] == "failed"),
            "running_steps": sum(1 for step in steps if step["status"] == "running"),
            "skipped_steps": sum(1 for step in steps if step["status"] == "skipped"),
            "last_valid_step": self.last_valid_step(),
            "is_completed": self.is_completed(),
            "certification": self.certification_status(),
            "steps": steps,
        }

    def history(self) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for step_state in self._step_order():
            checkpoint = self.storage.load_checkpoint(step_state["step_id"])
            if checkpoint is None:
                items.append(
                    {
                        "step_id": step_state["step_id"],
                        "status": step_state.get("status"),
                        "checkpoint_present": False,
                    }
                )
                continue

            items.append(
                {
                    "step_id": checkpoint["step_id"],
                    "status": checkpoint["status"],
                    "started_at": checkpoint.get("started_at"),
                    "completed_at": checkpoint.get("completed_at"),
                    "inputs_count": len(checkpoint.get("inputs", [])),
                    "outputs_count": len(checkpoint.get("outputs", [])),
                    "metrics_present": bool(checkpoint.get("metrics")),
                    "checkpoint_hash": checkpoint.get("checkpoint_hash"),
                    "previous_checkpoint_hash": checkpoint.get("previous_checkpoint_hash"),
                    "checkpoint_present": True,
                }
            )

        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "project": self.project,
            "steps_count": len(items),
            "last_valid_step": self.last_valid_step(),
            "certification": self.certification_status(),
            "history": items,
        }

    def last_valid_step(self) -> str | None:
        for step in reversed(self._step_order()):
            if step.get("status") == "completed":
                return step["step_id"]
        return None

    def is_completed(self) -> bool:
        steps = self._step_order()
        return bool(steps) and all(step.get("status") in {"completed", "skipped"} for step in steps)

    def export_manifest(self, path: str | None = None) -> dict[str, Any]:
        completed_steps = []
        failed_steps = 0
        chain = []
        for step_state in self._step_order():
            checkpoint = self.storage.load_checkpoint(step_state["step_id"])
            if not checkpoint:
                continue
            chain_item = {
                "step_id": checkpoint["step_id"],
                "status": checkpoint["status"],
                "checkpoint_hash": checkpoint["checkpoint_hash"],
            }
            if checkpoint.get("previous_checkpoint_hash") is not None:
                chain_item["previous_checkpoint_hash"] = checkpoint.get("previous_checkpoint_hash")
            chain.append(chain_item)
            if checkpoint["status"] == "completed":
                completed_steps.append(checkpoint)
            if checkpoint["status"] == "failed":
                failed_steps += 1

        manifest = {
            "schema_version": "HREVN_WORKFLOW_MANIFEST_v0.1",
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "project": self.project,
            "created_at": self._state["created_at"],
            "exported_at": utc_now(),
            "status": "completed" if self.is_completed() else "in_progress",
            "steps_count": len(chain),
            "completed_steps": len(completed_steps),
            "failed_steps": failed_steps,
            "last_valid_step": self.last_valid_step(),
            "checkpoint_chain": chain,
            "certifiable_deliverables": build_deliverables_from_steps(completed_steps),
        }

        target_path = Path(path) if path else self.storage.manifests_dir / "workflow_manifest.json"
        self.storage.save_json(target_path, manifest)
        self._track_event(
            "workflow_manifest_exported",
            manifest_path=str(target_path),
            workflow_status=manifest["status"],
            completed_steps=manifest["completed_steps"],
            failed_steps=manifest["failed_steps"],
            deliverables_count=len(manifest["certifiable_deliverables"]),
        )
        self._integrated_certify(target_path)
        return manifest

    def inspect_step(self, step_id: str) -> dict[str, Any]:
        checkpoint = self.storage.load_checkpoint(step_id)
        if checkpoint is None:
            raise FileNotFoundError(f"No checkpoint found for step_id={step_id}")

        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "step_id": step_id,
            "status": checkpoint.get("status"),
            "has_inputs": bool(checkpoint.get("inputs")),
            "has_outputs": bool(checkpoint.get("outputs")),
            "metrics_present": bool(checkpoint.get("metrics")),
            "checkpoint": checkpoint,
        }

    def doctor(self, manifest_path: str | None = None) -> dict[str, Any]:
        manifest_file = Path(manifest_path) if manifest_path else self.storage.manifests_dir / "workflow_manifest.json"
        verify_result = self.verify(manifest_path=str(manifest_file) if manifest_file.exists() else None)
        state = self.status()
        history = self.history()
        certification = self.certification_status()

        summary = {
            "state_present": self.storage.state_path.exists(),
            "checkpoints_count": len(history["history"]),
            "manifest_present": manifest_file.exists(),
            "last_valid_step": state["last_valid_step"],
            "is_completed": state["is_completed"],
            "verify_ok": verify_result["ok"],
            "issues_count": len(verify_result["issues"]),
            "certification_status": certification.get("status") if certification else None,
            "certification_ok": certification.get("ok") if certification else None,
        }

        result = {
            "ok": verify_result["ok"],
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "summary": summary,
            "certification": certification,
            "checks": verify_result["checks"],
            "issues": verify_result["issues"],
        }
        self._track_event(
            "workflow_doctor_run",
            manifest_path=str(manifest_file),
            verify_ok=verify_result["ok"],
            issues_count=len(verify_result["issues"]),
            certification_status=summary["certification_status"],
            certification_ok=summary["certification_ok"],
        )
        return result

    def list_deliverables(self, manifest_path: str | None = None) -> dict[str, Any]:
        target_manifest_path = Path(manifest_path) if manifest_path else self.storage.manifests_dir / "workflow_manifest.json"
        manifest = self.storage.load_json(target_manifest_path)
        if manifest is None:
            manifest = self.export_manifest(str(target_manifest_path))

        items: list[dict[str, Any]] = []
        for deliverable in manifest.get("certifiable_deliverables", []):
            path = deliverable.get("path")
            if not path:
                continue
            file_path = Path(path)
            current = file_metadata(file_path)
            mime_type, _ = mimetypes.guess_type(file_path.name)
            sha256_value = current.get("sha256")
            items.append(
                {
                    "filename": file_path.name,
                    "role": deliverable.get("role", "workflow_output"),
                    "path": str(file_path),
                    "exists": current.get("exists"),
                    "size_bytes": current.get("size_bytes"),
                    "sha256": sha256_value,
                    "sha256_short": sha256_value[:12] if isinstance(sha256_value, str) else None,
                    "type": mime_type or "application/octet-stream",
                }
            )

        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "manifest_path": str(target_manifest_path),
            "deliverables_count": len(items),
            "deliverables": items,
        }

    def telemetry_summary(self) -> dict[str, Any]:
        events = self.storage.load_telemetry_events()
        certification_counts = {
            "generated": 0,
            "failed": 0,
            "not_configured": 0,
            "blocked_by_local_integrity": 0,
            "other": 0,
        }
        workflows_initialized = 0
        manifests_exported = 0
        doctor_runs = 0
        resets = 0

        for event in events:
            event_type = event.get("event_type")
            if event_type == "workflow_initialized":
                workflows_initialized += 1
            elif event_type == "workflow_manifest_exported":
                manifests_exported += 1
            elif event_type == "workflow_doctor_run":
                doctor_runs += 1
            elif event_type == "workflow_reset":
                resets += 1
            elif event_type == "workflow_certification_recorded":
                status = event.get("certification_status")
                if status in certification_counts:
                    certification_counts[status] += 1
                else:
                    certification_counts["other"] += 1

        return {
            "installation_id": self.storage.load_or_create_installation_id(),
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "project": self.project,
            "total_events": len(events),
            "workflows_initialized": workflows_initialized,
            "manifests_exported": manifests_exported,
            "doctor_runs": doctor_runs,
            "resets": resets,
            "certifications": certification_counts,
            "last_event": events[-1] if events else None,
        }

    def to_verified_record_payload(
        self,
        case_reference: dict | None = None,
        manifest_path: str | None = None,
    ) -> dict:
        target_manifest_path = Path(manifest_path) if manifest_path else self.storage.manifests_dir / "workflow_manifest.json"
        verify_result = self.verify(manifest_path=str(target_manifest_path) if target_manifest_path.exists() else None)
        if not verify_result["ok"]:
            raise WorkflowIntegrityError(
                "Cannot build Verified Record payload from a workflow that fails integrity checks."
            )
        manifest = self.storage.load_json(target_manifest_path)
        if manifest is None:
            manifest = self.export_manifest(str(target_manifest_path))
        return build_verified_record_payload(target_manifest_path, manifest, case_reference=case_reference)

    def certification_status(self) -> dict[str, Any] | None:
        return self.storage.load_certification_status()

    def verify(self, manifest_path: str | None = None) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []
        completed_steps: list[dict[str, Any]] = []
        previous_completed_hash: str | None = None

        for step_state in self._step_order():
            step_id = step_state["step_id"]
            checkpoint = self.storage.load_checkpoint(step_id)
            if checkpoint is None:
                issues.append({"step_id": step_id, "kind": "missing_checkpoint_file"})
                continue

            expected_hash = checkpoint_hash(checkpoint)
            if checkpoint.get("checkpoint_hash") != expected_hash:
                issues.append(
                    {
                        "step_id": step_id,
                        "kind": "checkpoint_hash_mismatch",
                        "expected": expected_hash,
                        "found": checkpoint.get("checkpoint_hash"),
                    }
                )

            if checkpoint.get("status") == "completed":
                expected_previous = previous_completed_hash
                if checkpoint.get("previous_checkpoint_hash") != expected_previous:
                    issues.append(
                        {
                            "step_id": step_id,
                            "kind": "previous_checkpoint_hash_mismatch",
                            "expected": expected_previous,
                            "found": checkpoint.get("previous_checkpoint_hash"),
                        }
                    )
                previous_completed_hash = checkpoint.get("checkpoint_hash")
                completed_steps.append(checkpoint)

            for group in ("inputs", "outputs"):
                for item in checkpoint.get(group, []):
                    current = file_metadata(item["path"])
                    if current != item:
                        issues.append(
                            {
                                "step_id": step_id,
                                "kind": f"{group[:-1]}_metadata_mismatch",
                                "path": item["path"],
                                "expected": item,
                                "found": current,
                            }
                        )

        manifest_file = Path(manifest_path) if manifest_path else self.storage.manifests_dir / "workflow_manifest.json"
        if manifest_file.exists():
            manifest = self.storage.load_json(manifest_file)
            if manifest is None:
                issues.append({"kind": "manifest_unreadable", "path": str(manifest_file)})
            else:
                expected_chain = []
                for checkpoint in completed_steps + [
                    self.storage.load_checkpoint(step["step_id"])
                    for step in self._step_order()
                    if self.storage.load_checkpoint(step["step_id"]) and self.storage.load_checkpoint(step["step_id"])["status"] != "completed"
                ]:
                    if checkpoint is None:
                        continue
                    item = {
                        "step_id": checkpoint["step_id"],
                        "status": checkpoint["status"],
                        "checkpoint_hash": checkpoint["checkpoint_hash"],
                    }
                    if checkpoint.get("previous_checkpoint_hash") is not None:
                        item["previous_checkpoint_hash"] = checkpoint.get("previous_checkpoint_hash")
                    expected_chain.append(item)

                expected_deliverables = build_deliverables_from_steps(completed_steps)
                if manifest.get("workflow_id") != self.workflow_id:
                    issues.append(
                        {"kind": "manifest_workflow_id_mismatch", "expected": self.workflow_id, "found": manifest.get("workflow_id")}
                    )
                if manifest.get("run_id") != self.run_id:
                    issues.append({"kind": "manifest_run_id_mismatch", "expected": self.run_id, "found": manifest.get("run_id")})
                if manifest.get("last_valid_step") != self.last_valid_step():
                    issues.append(
                        {
                            "kind": "manifest_last_valid_step_mismatch",
                            "expected": self.last_valid_step(),
                            "found": manifest.get("last_valid_step"),
                        }
                    )
                if manifest.get("checkpoint_chain") != expected_chain:
                    issues.append({"kind": "manifest_checkpoint_chain_mismatch", "path": str(manifest_file)})
                if manifest.get("certifiable_deliverables") != expected_deliverables:
                    issues.append({"kind": "manifest_deliverables_mismatch", "path": str(manifest_file)})
                checks.append({"kind": "manifest_checked", "path": str(manifest_file)})
        else:
            checks.append({"kind": "manifest_not_present", "path": str(manifest_file)})

        checks.append({"kind": "checkpoint_count", "count": len(self._step_order())})
        return {
            "ok": not issues,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "last_valid_step": self.last_valid_step(),
            "checks": checks,
            "issues": issues,
        }

    def _integrated_certify(self, manifest_path: Path) -> None:
        verify_result = self.verify(manifest_path=str(manifest_path))
        if not verify_result["ok"]:
            blocked_payload = {
                "ok": False,
                "status": "blocked_by_local_integrity",
                "error": "Local integrity verification failed before remote certification.",
                "manifest_path": str(manifest_path),
                "workflow_id": self.workflow_id,
                "run_id": self.run_id,
                "issues": verify_result["issues"],
            }
            self.storage.save_certification_status(blocked_payload)
            self._track_event(
                "workflow_certification_recorded",
                manifest_path=str(manifest_path),
                certification_status=blocked_payload["status"],
                certification_ok=blocked_payload["ok"],
                issues_count=len(verify_result["issues"]),
                error=blocked_payload["error"],
            )
            return

        verified_record_payload = self.to_verified_record_payload(manifest_path=str(manifest_path))
        settings = load_certification_settings()
        if not settings.installation_id:
            settings = replace(settings, installation_id=self.storage.load_or_create_installation_id())
        result = certify_manifest(
            workflow_id=self.workflow_id,
            run_id=self.run_id,
            project=self.project,
            manifest_path=manifest_path,
            verified_record_payload=verified_record_payload,
            settings=settings,
        )
        payload = result.to_dict()
        payload["manifest_path"] = str(manifest_path)
        payload["workflow_id"] = self.workflow_id
        payload["run_id"] = self.run_id
        self.storage.save_certification_status(payload)
        self._track_event(
            "workflow_certification_recorded",
            manifest_path=str(manifest_path),
            certification_status=payload["status"],
            certification_ok=payload["ok"],
            bundle_id=payload.get("bundle_id"),
            record_id=payload.get("record_id"),
            error=payload.get("error"),
        )

    def reset(self, step_id: str | None = None) -> None:
        if step_id is None:
            shutil.rmtree(self.storage.root, ignore_errors=True)
            self.storage.ensure()
            self._state = self._new_state()
            self.run_id = self._state["run_id"]
            self._save_state()
            self._track_event("workflow_reset", reset_mode="full")
            return

        steps = self._step_order()
        remove = False
        kept_steps = []
        for step in steps:
            if step["step_id"] == step_id:
                remove = True
            if remove:
                self.storage.delete_checkpoint(step["step_id"])
            else:
                kept_steps.append(step)
        self._state["steps"] = kept_steps
        self._save_state()
        self._track_event("workflow_reset", reset_mode="from_step", step_id=step_id, remaining_steps=len(kept_steps))
