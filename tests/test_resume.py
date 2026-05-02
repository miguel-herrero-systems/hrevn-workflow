from pathlib import Path

import pytest

from hrevn_workflow import Workflow


def test_should_run_false_if_completed_and_inputs_unchanged(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_resume", storage_path=tmp_path / ".hrevn")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])

    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is False


def test_should_run_true_if_input_changes(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_input_change", storage_path=tmp_path / ".hrevn")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("done", encoding="utf-8")
        step.complete(outputs=[str(output_path)])

    input_path.write_text("changed", encoding="utf-8")

    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True


def test_exception_marks_step_failed(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("hello", encoding="utf-8")
    wf = Workflow("wf_fail", storage_path=tmp_path / ".hrevn")

    with pytest.raises(RuntimeError):
        with wf.step("01_step", inputs=[str(input_path)]) as step:
            assert step.should_run() is True
            raise RuntimeError("boom")

    checkpoint = wf.storage.load_checkpoint("01_step")
    assert checkpoint["status"] == "failed"


def test_reset_from_step_allows_rerun(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    mid_path = tmp_path / "mid.txt"
    out_path = tmp_path / "out.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_reset", storage_path=tmp_path / ".hrevn")
    with wf.step("01_first", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        mid_path.write_text("middle", encoding="utf-8")
        step.complete(outputs=[str(mid_path)])

    with wf.step("02_second", inputs=[str(mid_path)]) as step:
        assert step.should_run() is True
        out_path.write_text("final", encoding="utf-8")
        step.complete(outputs=[str(out_path)])

    wf.reset("02_second")

    with wf.step("02_second", inputs=[str(mid_path)]) as step:
        assert step.should_run() is True
