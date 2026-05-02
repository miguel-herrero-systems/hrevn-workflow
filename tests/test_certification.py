from pathlib import Path

from hrevn_workflow import Workflow


def test_export_manifest_records_not_configured_certification_by_default(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    manifest_path = tmp_path / "workflow_manifest.json"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_cert_default", storage_path=tmp_path / ".hrevn", project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])

    wf.export_manifest(str(manifest_path))
    certification = wf.certification_status()
    assert certification is not None
    assert certification["ok"] is False
    assert certification["status"] == "not_configured"


def test_export_manifest_records_generated_certification_when_runtime_available(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    manifest_path = tmp_path / "workflow_manifest.json"
    input_path.write_text("hello", encoding="utf-8")

    monkeypatch.setenv("HREVN_API_BASE_URL", "https://api.hrevn.test")
    monkeypatch.setenv("HREVN_API_KEY", "test-key")

    def fake_submit_generate_bundle(api_base_url: str, api_key: str, payload: dict) -> dict:
        assert api_base_url == "https://api.hrevn.test"
        assert api_key == "test-key"
        assert payload["record"]["case_reference"]["workflow_id"] == "wf_cert_live"
        return {
            "output_version": "1.0",
            "result": "GENERATED",
            "bundle_id": "BND-TEST123456",
            "download_url": "/v1/bundles/BND-TEST123456/download",
            "expires_at": "2026-05-03T10:00:00Z",
            "metadata": {
                "record_id": "AER-TEST3456",
                "schema_version": "hrevn-aer-v0.3.3",
            },
        }

    monkeypatch.setattr("hrevn_workflow.certification.submit_generate_bundle", fake_submit_generate_bundle)

    wf = Workflow("wf_cert_live", storage_path=tmp_path / ".hrevn", project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])

    wf.export_manifest(str(manifest_path))
    certification = wf.certification_status()
    assert certification is not None
    assert certification["ok"] is True
    assert certification["status"] == "generated"
    assert certification["bundle_id"] == "BND-TEST123456"
    assert certification["record_id"] == "AER-TEST3456"


def test_export_manifest_blocks_certification_when_local_integrity_fails(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    manifest_path = tmp_path / "workflow_manifest.json"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_cert_blocked", storage_path=tmp_path / ".hrevn", project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])

    wf.export_manifest(str(manifest_path))
    output_path.write_text("tampered", encoding="utf-8")
    wf.export_manifest(str(manifest_path))
    certification = wf.certification_status()
    assert certification is not None
    assert certification["ok"] is False
    assert certification["status"] == "blocked_by_local_integrity"
