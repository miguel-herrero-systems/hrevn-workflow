from __future__ import annotations

import json
from pathlib import Path

from hrevn_workflow import Workflow

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "input_document.txt"
TEXT_PATH = BASE_DIR / "extracted_text.md"
ANALYSIS_PATH = BASE_DIR / "analysis.json"
INTAKE_CASE_PATH = BASE_DIR / "intake_case.json"
REPORT_PATH = BASE_DIR / "client_review_report.md"
PACKAGE_PATH = BASE_DIR / "client_packet.json"
MANIFEST_PATH = BASE_DIR / "workflow_manifest.json"


def ensure_input() -> None:
    if not INPUT_PATH.exists():
        INPUT_PATH.write_text(
            "\n".join(
                [
                    "Document title: AI customer support workflow",
                    "Owner: Operations team",
                    "Context: Customer-facing chatbot used on website support pages.",
                    "Known questions: user notice, escalation to human, retained logs, provider controls.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def extract_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    return "# Extracted workflow text\n\n" + raw


def call_llm(text: str) -> str:
    payload = {
        "summary": "Customer-facing chatbot workflow with documentation gaps.",
        "source_excerpt": text[:120],
        "risk_flags": [
            "transparency_notice_missing",
            "human_escalation_needs_review",
            "provider_controls_not_confirmed",
        ],
        "recommended_next_step": "prepare_review_report",
        "status": "ready",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report(analysis_text: str) -> str:
    analysis = json.loads(analysis_text)
    lines = [
        "# Workflow Review Report",
        "",
        "## Summary",
        analysis["summary"],
        "",
        "## Risk flags",
    ]
    lines.extend([f"- {item}" for item in analysis["risk_flags"]])
    lines.extend(
        [
            "",
            "## Recommended next step",
            analysis["recommended_next_step"],
            "",
            "## Status",
            analysis["status"],
        ]
    )
    return "\n".join(lines) + "\n"


def build_intake_case(analysis_text: str) -> str:
    analysis = json.loads(analysis_text)
    payload = {
        "case_id": "demo-ai-review-case-001",
        "product": "ai_review",
        "title": "Customer support chatbot AI review",
        "summary": analysis["summary"],
        "risk_flags": analysis["risk_flags"],
        "review_owner": "Operations compliance",
        "next_action": analysis["recommended_next_step"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_client_packet(report_path: Path, intake_case_path: Path) -> str:
    payload = {
        "package_id": "demo-client-packet-001",
        "deliverables": [
            {
                "role": "client_review_report",
                "path": report_path.name,
            },
            {
                "role": "structured_case",
                "path": intake_case_path.name,
            },
        ],
        "delivery_note": "This package simulates the final outputs prepared for a client-facing AI review.",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    ensure_input()
    wf = Workflow(
        workflow_id="ai_review_pipeline_001",
        storage_path=BASE_DIR / ".hrevn",
        project="examples",
    )

    with wf.step("01_extract_text", inputs=[str(INPUT_PATH)]) as step:
        if step.should_run():
            text = extract_text(INPUT_PATH)
            TEXT_PATH.write_text(text, encoding="utf-8")
            step.complete(outputs=[str(TEXT_PATH)])
            print("01_extract_text: executed")
        else:
            print("01_extract_text: skipped")

    with wf.step("02_llm_analysis", inputs=[str(TEXT_PATH)]) as step:
        if step.should_run():
            result = call_llm(TEXT_PATH.read_text(encoding="utf-8"))
            ANALYSIS_PATH.write_text(result, encoding="utf-8")
            step.complete(
                outputs=[str(ANALYSIS_PATH)],
                model_used="gpt-4.1",
                tokens_in=5000,
                tokens_out=1200,
            )
            print("02_llm_analysis: executed")
        else:
            print("02_llm_analysis: skipped")

    with wf.step("03_build_intake_case", inputs=[str(ANALYSIS_PATH)]) as step:
        if step.should_run():
            intake_case = build_intake_case(ANALYSIS_PATH.read_text(encoding="utf-8"))
            INTAKE_CASE_PATH.write_text(intake_case, encoding="utf-8")
            step.complete(outputs=[str(INTAKE_CASE_PATH)], artifact_type="structured_case_json")
            print("03_build_intake_case: executed")
        else:
            print("03_build_intake_case: skipped")

    with wf.step("04_issue_client_package", inputs=[str(ANALYSIS_PATH), str(INTAKE_CASE_PATH)]) as step:
        if step.should_run():
            report = build_report(ANALYSIS_PATH.read_text(encoding="utf-8"))
            REPORT_PATH.write_text(report, encoding="utf-8")
            client_packet = build_client_packet(REPORT_PATH, INTAKE_CASE_PATH)
            PACKAGE_PATH.write_text(client_packet, encoding="utf-8")
            step.complete(
                outputs=[str(REPORT_PATH), str(PACKAGE_PATH)],
                report_type="markdown",
                delivery_mode="client_packet",
            )
            print("04_issue_client_package: executed")
        else:
            print("04_issue_client_package: skipped")

    print(wf.status())
    print("last_valid_step:", wf.last_valid_step())
    wf.export_manifest(str(MANIFEST_PATH))
    print("manifest:", MANIFEST_PATH)


if __name__ == "__main__":
    main()
