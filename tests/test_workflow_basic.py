from pathlib import Path

from hrevn_workflow import Workflow


def test_create_workflow_and_complete_step(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_basic", storage_path=tmp_path / ".hrevn")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        payload = step.complete(outputs=[str(output_path)])

    assert payload["status"] == "completed"
    assert wf.last_valid_step() == "01_step"
    status = wf.status()
    assert status["completed_steps"] == 1
