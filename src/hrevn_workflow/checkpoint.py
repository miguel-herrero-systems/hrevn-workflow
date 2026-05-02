from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .errors import StepStateError
from .hashing import checkpoint_hash, file_metadata

if TYPE_CHECKING:
    from .workflow import Workflow


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class Step:
    workflow: "Workflow"
    step_id: str
    input_paths: list[str] = field(default_factory=list)
    metadata: dict[str, Any] | None = None
    existing_checkpoint: dict[str, Any] | None = None
    _status_started: bool = False
    _metrics: dict[str, Any] = field(default_factory=dict)
    _closed: bool = False

    def __enter__(self) -> "Step":
        self.existing_checkpoint = self.workflow.storage.load_checkpoint(self.step_id)
        return self

    def __exit__(self, exc_type, exc, _tb) -> bool:
        if exc_type is not None:
            self.fail(exc)
            return False
        if self._status_started and not self._closed:
            self.fail("Step exited without complete(), fail() or skip().")
        return False

    def _input_metadata(self) -> list[dict[str, Any]]:
        return [file_metadata(path) for path in self.input_paths]

    def _existing_inputs_match(self) -> bool:
        if not self.existing_checkpoint:
            return False
        return self.existing_checkpoint.get("inputs", []) == self._input_metadata()

    def should_run(self) -> bool:
        if (
            self.existing_checkpoint
            and self.existing_checkpoint.get("status") == "completed"
            and self._existing_inputs_match()
        ):
            return False

        if not self._status_started:
            draft = self._base_payload(status="running")
            self.workflow.storage.save_checkpoint(self.step_id, draft)
            self.workflow._upsert_step_state(self.step_id, "running", draft.get("checkpoint_hash"))
            self._status_started = True
        return True

    def record_metrics(self, **metrics: Any) -> None:
        self._metrics.update(metrics)

    def complete(self, outputs: list[str] | None = None, **metrics: Any) -> dict[str, Any]:
        self.record_metrics(**metrics)
        payload = self._final_payload(status="completed", outputs=outputs or [], error=None, resume_hint=None)
        self._persist(payload)
        return payload

    def fail(self, error: Exception | str, resume_hint: str | None = None) -> dict[str, Any]:
        payload = self._final_payload(
            status="failed",
            outputs=self.existing_checkpoint.get("outputs", []) if self.existing_checkpoint else [],
            error=str(error),
            resume_hint=resume_hint,
        )
        self._persist(payload)
        return payload

    def skip(self, reason: str | None = None) -> dict[str, Any]:
        payload = self._final_payload(status="skipped", outputs=[], error=reason, resume_hint=None)
        self._persist(payload)
        return payload

    def _base_payload(self, status: str) -> dict[str, Any]:
        previous_hash = self.workflow.previous_completed_hash(exclude_step_id=self.step_id)
        payload = {
            "schema_version": "HREVN_WORKFLOW_CHECKPOINT_v0.1",
            "workflow_id": self.workflow.workflow_id,
            "run_id": self.workflow.run_id,
            "step_id": self.step_id,
            "status": status,
            "started_at": self.existing_checkpoint.get("started_at") if self.existing_checkpoint else utc_now(),
            "inputs": self._input_metadata(),
            "outputs": [],
            "previous_checkpoint_hash": previous_hash,
        }
        if self.workflow.project:
            payload["project"] = self.workflow.project
        if self.metadata:
            payload["metadata"] = self.metadata
        payload["checkpoint_hash"] = checkpoint_hash(payload)
        return payload

    def _final_payload(
        self,
        status: str,
        outputs: list[str] | list[dict[str, Any]],
        error: str | None,
        resume_hint: str | None,
    ) -> dict[str, Any]:
        base = self._base_payload(status=status)
        output_metadata = outputs
        if outputs and isinstance(outputs[0], str):
            output_metadata = [file_metadata(path) for path in outputs]  # type: ignore[index]
        base["outputs"] = output_metadata
        if status in {"completed", "failed", "skipped"}:
            base["completed_at"] = utc_now()
        if self._metrics:
            base["metrics"] = dict(self._metrics)
        if error is not None:
            base["error"] = error
        else:
            base["error"] = None
        base["resume_hint"] = resume_hint
        base["checkpoint_hash"] = checkpoint_hash(base)
        return base

    def _persist(self, payload: dict[str, Any]) -> None:
        self.workflow.storage.save_checkpoint(self.step_id, payload)
        self.workflow._upsert_step_state(self.step_id, payload["status"], payload["checkpoint_hash"])
        self.existing_checkpoint = payload
        self._closed = True
        self._status_started = False
