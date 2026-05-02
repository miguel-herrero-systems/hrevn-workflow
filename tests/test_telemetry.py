import json
from pathlib import Path

from hrevn_workflow import Workflow
from hrevn_workflow.storage import WorkflowStorage


def _prepare_workflow(tmp_path: Path) -> tuple[Workflow, Path, Path]:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_telemetry", storage_path=tmp_path / ".hrevn", project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])
    return wf, input_path, output_path


def test_installation_id_is_persistent(tmp_path: Path) -> None:
    storage = WorkflowStorage(tmp_path / ".hrevn")
    first = storage.load_or_create_installation_id()
    second = storage.load_or_create_installation_id()

    assert first == second
    payload = json.loads(storage.installation_path.read_text(encoding="utf-8"))
    assert payload["installation_id"] == first


def test_manifest_and_doctor_append_telemetry_events(tmp_path: Path) -> None:
    wf, _, _ = _prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"

    wf.export_manifest(str(manifest_path))
    wf.doctor(str(manifest_path))

    events = wf.storage.load_telemetry_events()
    event_types = [event["event_type"] for event in events]

    assert event_types[0] == "workflow_initialized"
    assert "workflow_manifest_exported" in event_types
    assert "workflow_certification_recorded" in event_types
    assert event_types[-1] == "workflow_doctor_run"

    install_ids = {event["installation_id"] for event in events}
    assert len(install_ids) == 1


def test_generated_certification_reuses_installation_id_in_remote_request(tmp_path: Path, monkeypatch) -> None:
    wf, _, _ = _prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"

    monkeypatch.setenv("HREVN_API_BASE_URL", "https://api.hrevn.test")
    monkeypatch.setenv("HREVN_API_KEY", "test-key")

    captured: dict[str, str] = {}

    def fake_submit_generate_bundle(api_base_url: str, api_key: str, payload: dict) -> dict:
        captured["api_base_url"] = api_base_url
        captured["api_key"] = api_key
        captured["installation_id"] = payload["record"]["installation_id"]
        return {
            "output_version": "1.0",
            "result": "GENERATED",
            "bundle_id": "BND-TEST123456",
            "download_url": "/v1/bundles/BND-TEST123456/download",
            "expires_at": "2026-05-03T10:00:00Z",
            "metadata": {"record_id": "AER-TEST3456"},
        }

    monkeypatch.setattr("hrevn_workflow.certification.submit_generate_bundle", fake_submit_generate_bundle)

    expected_installation_id = wf.storage.load_or_create_installation_id()
    wf.export_manifest(str(manifest_path))

    assert captured["api_base_url"] == "https://api.hrevn.test"
    assert captured["api_key"] == "test-key"
    assert captured["installation_id"] == expected_installation_id

    certification = wf.certification_status()
    assert certification is not None
    assert certification["status"] == "generated"

