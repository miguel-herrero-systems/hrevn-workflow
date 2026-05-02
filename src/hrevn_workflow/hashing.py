from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def file_metadata(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return {
            "path": str(path),
            "sha256": None,
            "size_bytes": None,
            "exists": False,
        }

    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "size_bytes": file_path.stat().st_size,
        "exists": True,
    }


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def checkpoint_hash(payload: dict[str, Any]) -> str:
    canonical_payload = dict(payload)
    canonical_payload.pop("checkpoint_hash", None)
    return sha256_text(canonical_json(canonical_payload))
