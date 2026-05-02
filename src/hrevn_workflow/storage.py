from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .hashing import canonical_json


class WorkflowStorage:
    def __init__(self, storage_path: str | Path) -> None:
        self.root = Path(storage_path)
        self.checkpoints_dir = self.root / "checkpoints"
        self.manifests_dir = self.root / "manifests"
        self.certification_dir = self.root / "certification"
        self.state_path = self.root / "workflow_state.json"
        self.ensure()

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.certification_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint_path(self, step_id: str) -> Path:
        return self.checkpoints_dir / f"{step_id}.json"

    def load_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(payload) + "\n", encoding="utf-8")

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
