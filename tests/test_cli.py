import json
from pathlib import Path

from hrevn_workflow.cli import main
from hrevn_workflow import Workflow


def prepare_workflow(tmp_path: Path) -> Path:
    storage_path = tmp_path / ".hrevn"
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_cli", storage_path=storage_path, project="tests")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])
    return storage_path


def test_cli_status_outputs_json(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    code = main(["--storage-path", str(storage_path), "status"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["workflow_id"] == "wf_cli"
    assert payload["completed_steps"] == 1


def test_cli_history_outputs_compact_checkpoint_chain(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    code = main(["--storage-path", str(storage_path), "history"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["workflow_id"] == "wf_cli"
    assert payload["steps_count"] == 1
    assert payload["history"][0]["step_id"] == "01_step"
    assert payload["history"][0]["status"] == "completed"
    assert payload["history"][0]["inputs_count"] == 1
    assert payload["history"][0]["outputs_count"] == 1


def test_cli_telemetry_summary_outputs_local_counts(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"
    manifest_code = main(["--storage-path", str(storage_path), "manifest", "--path", str(manifest_path)])
    assert manifest_code == 0
    _ = capsys.readouterr()

    doctor_code = main(["--storage-path", str(storage_path), "doctor", "--manifest-path", str(manifest_path)])
    assert doctor_code == 0
    _ = capsys.readouterr()

    code = main(["--storage-path", str(storage_path), "telemetry-summary"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["workflow_id"] == "wf_cli"
    assert payload["installation_id"].startswith("inst-")
    assert payload["workflows_initialized"] == 1
    assert payload["manifests_exported"] == 1
    assert payload["doctor_runs"] == 1
    assert payload["certifications"]["not_configured"] == 1
    assert payload["last_event"]["event_type"] == "workflow_doctor_run"


def test_cli_doctor_outputs_health_summary(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"
    manifest_code = main(["--storage-path", str(storage_path), "manifest", "--path", str(manifest_path)])
    assert manifest_code == 0
    _ = capsys.readouterr()

    code = main(["--storage-path", str(storage_path), "doctor", "--manifest-path", str(manifest_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["ok"] is True
    assert payload["summary"]["state_present"] is True
    assert payload["summary"]["manifest_present"] is True
    assert payload["summary"]["verify_ok"] is True
    assert payload["summary"]["checkpoints_count"] == 1


def test_cli_manifest_exports_file(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"
    code = main(["--storage-path", str(storage_path), "manifest", "--path", str(manifest_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert manifest_path.exists()
    assert payload["schema_version"] == "HREVN_WORKFLOW_MANIFEST_v0.1"


def test_cli_list_deliverables_outputs_certifiable_files(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"
    manifest_code = main(["--storage-path", str(storage_path), "manifest", "--path", str(manifest_path)])
    assert manifest_code == 0
    _ = capsys.readouterr()

    code = main(
        [
            "--storage-path",
            str(storage_path),
            "list-deliverables",
            "--manifest-path",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["deliverables_count"] == 1
    assert payload["deliverables"][0]["filename"] == "output.txt"
    assert payload["deliverables"][0]["sha256_short"] is not None


def test_cli_record_payload_outputs_verified_record_shape(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    manifest_path = tmp_path / "workflow_manifest.json"
    manifest_code = main(["--storage-path", str(storage_path), "manifest", "--path", str(manifest_path)])
    assert manifest_code == 0
    _ = capsys.readouterr()

    code = main(
        [
            "--storage-path",
            str(storage_path),
            "record-payload",
            "--manifest-path",
            str(manifest_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["integration_profile"] == "hrevn_workflow_verified_state_v0.1"
    assert payload["case_reference"]["workflow_id"] == "wf_cli"
    assert payload["certified_deliverables"][0]["document_id"] == "workflow_manifest"
    assert payload["certified_deliverables"][1]["filename"] == "output.txt"


def test_cli_inspect_step_outputs_checkpoint_details(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    code = main(["--storage-path", str(storage_path), "inspect-step", "--step-id", "01_step"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["workflow_id"] == "wf_cli"
    assert payload["step_id"] == "01_step"
    assert payload["status"] == "completed"
    assert payload["has_inputs"] is True
    assert payload["has_outputs"] is True
    assert payload["checkpoint"]["outputs"][0]["path"].endswith("output.txt")


def test_cli_reset_from_step(tmp_path: Path, capsys) -> None:
    storage_path = prepare_workflow(tmp_path)
    code = main(["--storage-path", str(storage_path), "reset", "--step-id", "01_step"])
    captured = capsys.readouterr()
    assert code == 0
    assert "from step 01_step" in captured.out
