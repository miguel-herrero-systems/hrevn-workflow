import json
from pathlib import Path

from hrevn_workflow import Workflow
from hrevn_workflow.cli import main
from hrevn_workflow.errors import WorkflowIntegrityError


def build_verified_example(tmp_path: Path) -> tuple[Workflow, Path, Path]:
    storage_path = tmp_path / ".hrevn"
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    manifest_path = tmp_path / "workflow_manifest.json"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_verify", storage_path=storage_path, project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])
    wf.export_manifest(str(manifest_path))
    return wf, output_path, manifest_path


def test_verify_ok_for_clean_state(tmp_path: Path) -> None:
    wf, _output_path, manifest_path = build_verified_example(tmp_path)
    result = wf.verify(manifest_path=str(manifest_path))
    assert result["ok"] is True
    assert result["issues"] == []


def test_verify_detects_tampered_output(tmp_path: Path) -> None:
    wf, output_path, manifest_path = build_verified_example(tmp_path)
    output_path.write_text("tampered", encoding="utf-8")
    result = wf.verify(manifest_path=str(manifest_path))
    assert result["ok"] is False
    assert any(item["kind"] == "output_metadata_mismatch" for item in result["issues"])


def test_cli_verify_returns_nonzero_on_issue(tmp_path: Path, capsys) -> None:
    wf, output_path, manifest_path = build_verified_example(tmp_path)
    output_path.write_text("tampered", encoding="utf-8")
    code = main(
        [
            "--storage-path",
            str(wf.storage.root),
            "verify",
            "--manifest-path",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["ok"] is False


def test_doctor_reports_failed_integrity_after_tampering(tmp_path: Path) -> None:
    wf, output_path, manifest_path = build_verified_example(tmp_path)
    output_path.write_text("tampered", encoding="utf-8")
    result = wf.doctor(manifest_path=str(manifest_path))
    assert result["ok"] is False
    assert result["summary"]["verify_ok"] is False
    assert result["summary"]["issues_count"] >= 1
    assert any(item["kind"] == "output_metadata_mismatch" for item in result["issues"])


def test_verified_record_payload_refuses_tampered_workflow(tmp_path: Path) -> None:
    wf, output_path, manifest_path = build_verified_example(tmp_path)
    output_path.write_text("tampered", encoding="utf-8")
    try:
        wf.to_verified_record_payload(manifest_path=str(manifest_path))
    except WorkflowIntegrityError as exc:
        assert "fails integrity checks" in str(exc)
    else:
        raise AssertionError("Expected WorkflowIntegrityError for tampered workflow")


def test_cli_record_payload_returns_nonzero_on_integrity_issue(tmp_path: Path, capsys) -> None:
    wf, output_path, manifest_path = build_verified_example(tmp_path)
    output_path.write_text("tampered", encoding="utf-8")
    code = main(
        [
            "--storage-path",
            str(wf.storage.root),
            "record-payload",
            "--manifest-path",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "fails integrity checks" in captured.err
