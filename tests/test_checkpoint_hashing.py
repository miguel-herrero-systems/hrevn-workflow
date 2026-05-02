import json
from pathlib import Path

from hrevn_workflow import Workflow


def test_checkpoint_hash_changes_if_output_changes(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_hash", storage_path=tmp_path / ".hrevn")
    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("one", encoding="utf-8")
        first = step.complete(outputs=[str(output_path)])

    wf.reset("01_step")

    with wf.step("01_step", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        output_path.write_text("two", encoding="utf-8")
        second = step.complete(outputs=[str(output_path)])

    assert first["checkpoint_hash"] != second["checkpoint_hash"]


def test_previous_checkpoint_hash_chains_two_steps(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    mid_path = tmp_path / "mid.txt"
    out_path = tmp_path / "out.txt"
    input_path.write_text("hello", encoding="utf-8")

    wf = Workflow("wf_chain", storage_path=tmp_path / ".hrevn")
    with wf.step("01_first", inputs=[str(input_path)]) as step:
        assert step.should_run() is True
        mid_path.write_text("middle", encoding="utf-8")
        first = step.complete(outputs=[str(mid_path)])

    with wf.step("02_second", inputs=[str(mid_path)]) as step:
        assert step.should_run() is True
        out_path.write_text("final", encoding="utf-8")
        second = step.complete(outputs=[str(out_path)])

    assert second["previous_checkpoint_hash"] == first["checkpoint_hash"]
