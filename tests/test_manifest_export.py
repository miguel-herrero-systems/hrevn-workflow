from pathlib import Path

from hrevn_workflow import Workflow


def test_export_manifest_and_verified_record_payload(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.json"
    report_path = tmp_path / "report.md"
    manifest_path = tmp_path / "workflow_manifest.json"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_manifest", storage_path=tmp_path / ".hrevn", project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text('{"ok":true}', encoding="utf-8")
        report_path.write_text("# Report\n\nDone.\n", encoding="utf-8")
        step.complete(outputs=[str(output_path), str(report_path)], model_used="gpt-4.1")

    manifest = wf.export_manifest(str(manifest_path))
    assert manifest_path.exists()
    assert manifest["schema_version"] == "HREVN_WORKFLOW_MANIFEST_v0.1"
    assert manifest["last_valid_step"] == "01_step"
    assert manifest["completed_steps"] == 1
    assert manifest["certifiable_deliverables"][0]["path"] == str(output_path)
    assert manifest["certifiable_deliverables"][1]["path"] == str(report_path)

    payload = wf.to_verified_record_payload(manifest_path=str(manifest_path))
    assert payload["integration_profile"] == "hrevn_workflow_verified_state_v0.1"
    assert payload["case_reference"]["workflow_id"] == "wf_manifest"
    assert payload["workflow_summary"]["completed_steps"] == 1
    assert payload["certified_deliverables"][0]["filename"] == "workflow_manifest.json"
    assert payload["certified_deliverables"][1]["filename"] == "output.json"
    assert payload["certified_deliverables"][2]["filename"] == "report.md"
