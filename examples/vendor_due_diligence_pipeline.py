from __future__ import annotations

import json
from pathlib import Path

from hrevn_workflow import Workflow

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "vendor_brief.txt"
SUMMARY_PATH = BASE_DIR / "vendor_summary.md"
RISK_PATH = BASE_DIR / "vendor_risk_assessment.json"
QUESTIONNAIRE_PATH = BASE_DIR / "vendor_follow_up_questions.md"
MEMO_PATH = BASE_DIR / "vendor_due_diligence_memo.md"
MANIFEST_PATH = BASE_DIR / "vendor_workflow_manifest.json"


def ensure_input() -> None:
    if not INPUT_PATH.exists():
        INPUT_PATH.write_text(
            "\n".join(
                [
                    "Vendor: Orbit AI Services",
                    "Use case: External document classification API for insurance claims.",
                    "Known controls: SOC 2 claimed, human override not yet documented, retention period unclear.",
                    "Open questions: subprocessors, model update policy, incident escalation, EU processing footprint.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def summarize_vendor(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    return "# Vendor summary\n\n" + raw + "\n"


def assess_risk(summary_text: str) -> str:
    payload = {
        "vendor": "Orbit AI Services",
        "assessment_scope": "third_party_ai_due_diligence",
        "risk_level": "medium",
        "flags": [
            "retention_period_not_confirmed",
            "human_override_not_documented",
            "subprocessor_chain_needs_review",
        ],
        "recommended_action": "send_follow_up_questionnaire",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_questions(risk_text: str) -> str:
    risk = json.loads(risk_text)
    lines = [
        "# Vendor follow-up questions",
        "",
        f"Risk level: {risk['risk_level']}",
        "",
        "## Questions",
        "- Please confirm retention periods for uploaded claim materials.",
        "- Please describe how human override works in customer production flows.",
        "- Please list subprocessors involved in training, inference or support.",
        "- Please explain how material model updates are communicated.",
    ]
    return "\n".join(lines) + "\n"


def build_memo(summary_text: str, risk_text: str, questions_text: str) -> str:
    risk = json.loads(risk_text)
    lines = [
        "# Vendor due diligence memo",
        "",
        "## Initial view",
        "This vendor appears usable for further review, but only after documentary gaps are clarified.",
        "",
        "## Current risk level",
        risk["risk_level"],
        "",
        "## Main flags",
    ]
    lines.extend([f"- {flag}" for flag in risk["flags"]])
    lines.extend(
        [
            "",
            "## Summary basis",
            summary_text.strip(),
            "",
            "## Follow-up questionnaire prepared",
            questions_text.strip(),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    ensure_input()
    wf = Workflow(
        workflow_id="vendor_due_diligence_001",
        storage_path=BASE_DIR / ".hrevn_vendor",
        project="examples",
    )

    with wf.step("01_vendor_summary", inputs=[str(INPUT_PATH)]) as step:
        if step.should_run():
            SUMMARY_PATH.write_text(summarize_vendor(INPUT_PATH), encoding="utf-8")
            step.complete(outputs=[str(SUMMARY_PATH)])
            print("01_vendor_summary: executed")
        else:
            print("01_vendor_summary: skipped")

    with wf.step("02_risk_assessment", inputs=[str(SUMMARY_PATH)]) as step:
        if step.should_run():
            RISK_PATH.write_text(assess_risk(SUMMARY_PATH.read_text(encoding="utf-8")), encoding="utf-8")
            step.complete(outputs=[str(RISK_PATH)], assessment_type="vendor_risk")
            print("02_risk_assessment: executed")
        else:
            print("02_risk_assessment: skipped")

    with wf.step("03_follow_up_questions", inputs=[str(RISK_PATH)]) as step:
        if step.should_run():
            QUESTIONNAIRE_PATH.write_text(build_questions(RISK_PATH.read_text(encoding="utf-8")), encoding="utf-8")
            step.complete(outputs=[str(QUESTIONNAIRE_PATH)], artifact_type="questionnaire")
            print("03_follow_up_questions: executed")
        else:
            print("03_follow_up_questions: skipped")

    with wf.step("04_issue_due_diligence_memo", inputs=[str(SUMMARY_PATH), str(RISK_PATH), str(QUESTIONNAIRE_PATH)]) as step:
        if step.should_run():
            MEMO_PATH.write_text(
                build_memo(
                    SUMMARY_PATH.read_text(encoding="utf-8"),
                    RISK_PATH.read_text(encoding="utf-8"),
                    QUESTIONNAIRE_PATH.read_text(encoding="utf-8"),
                ),
                encoding="utf-8",
            )
            step.complete(outputs=[str(MEMO_PATH)], delivery_mode="vendor_memo")
            print("04_issue_due_diligence_memo: executed")
        else:
            print("04_issue_due_diligence_memo: skipped")

    print(wf.status())
    print("last_valid_step:", wf.last_valid_step())
    wf.export_manifest(str(MANIFEST_PATH))
    print("manifest:", MANIFEST_PATH)


if __name__ == "__main__":
    main()
