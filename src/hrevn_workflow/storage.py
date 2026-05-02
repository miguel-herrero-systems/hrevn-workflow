from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .hashing import canonical_json


class WorkflowStorage:
    def __init__(self, storage_path: str | Path) -> None:
        self.root = Path(storage_path)
        self.checkpoints_dir = self.root / "checkpoints"
        self.manifests_dir = self.root / "manifests"
        self.certification_dir = self.root / "certification"
        self.telemetry_dir = self.root / "telemetry"
        self.state_path = self.root / "workflow_state.json"
        self.ensure()

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.certification_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint_path(self, step_id: str) -> Path:
        return self.checkpoints_dir / f"{step_id}.json"

    def load_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(payload) + "\n", encoding="utf-8")

    def append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(payload) + "\n")

    def load_state(self) -> dict[str, Any] | None:
        return self.load_json(self.state_path)

    def save_state(self, payload: dict[str, Any]) -> None:
        self.save_json(self.state_path, payload)

    def load_checkpoint(self, step_id: str) -> dict[str, Any] | None:
        return self.load_json(self.checkpoint_path(step_id))

    def save_checkpoint(self, step_id: str, payload: dict[str, Any]) -> None:
        self.save_json(self.checkpoint_path(step_id), payload)

    def delete_checkpoint(self, step_id: str) -> None:
        path = self.checkpoint_path(step_id)
        if path.exists():
            path.unlink()

    def save_manifest(self, filename: str, payload: dict[str, Any]) -> Path:
        path = self.manifests_dir / filename
        self.save_json(path, payload)
        return path

    @property
    def certification_status_path(self) -> Path:
        return self.certification_dir / "status.json"

    def load_certification_status(self) -> dict[str, Any] | None:
        return self.load_json(self.certification_status_path)

    def save_certification_status(self, payload: dict[str, Any]) -> None:
        self.save_json(self.certification_status_path, payload)

    @property
    def telemetry_events_path(self) -> Path:
        return self.telemetry_dir / "events.jsonl"

    def append_telemetry_event(self, payload: dict[str, Any]) -> None:
        self.append_jsonl(self.telemetry_events_path, payload)

    def load_telemetry_events(self) -> list[dict[str, Any]]:
        if not self.telemetry_events_path.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in self.telemetry_events_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            items.append(json.loads(stripped))
        return items

    @property
    def installation_path(self) -> Path:
        return self.telemetry_dir / "installation.json"

    def load_or_create_installation_id(self) -> str:
        payload = self.load_json(self.installation_path)
        if payload and isinstance(payload.get("installation_id"), str) and payload["installation_id"].strip():
            return payload["installation_id"]

        installation_id = f"inst-{uuid4().hex[:12]}"
        self.save_json(
            self.installation_path,
            {
                "schema_version": "HREVN_WORKFLOW_INSTALLATION_v0.1",
                "installation_id": installation_id,
            },
        )
        return installation_id
