# hrevn-workflow

Checkpoint your AI workflows locally. Resume from the last valid step.
Optionally generate a verifiable execution record.

Most AI workflows fail in the worst possible moment. When that happens, developers often have to rerun everything from scratch. `hrevn-workflow` solves this by adding lightweight checkpoints to your workflow, so you can resume from the last valid step instead of starting over.

In the first minute, the important part is this:

- MIT-licensed local SDK
- local-first
- no API key required
- no file upload required
- no dashboard
- detects changed or tampered outputs
- adds HREVN certification when configured

The local SDK is free to use. HREVN Verified Record certification is currently included for early adopters when runtime credentials are configured.

Unlike observability tools, this SDK is:

- local-first
- lightweight
- independent from any platform
- focused on resumability, not dashboards

And when needed, it can generate a HREVN Verified Record to certify the execution.

HREVN Verified Record certification is currently included for early SDK users during the initial adoption phase. This avoids friction early while keeping the local SDK and the managed certification layer clearly separated.

This SDK solves workflow continuity. HREVN adds verifiable records when needed.

## Learn more

- Workflow continuity: [https://hrevn.com/en/workflow-continuity/](https://hrevn.com/en/workflow-continuity/)
- Verifiable AI records: [https://hrevn.com/en/verifiable-ai-records/](https://hrevn.com/en/verifiable-ai-records/)

## What it is

`hrevn-workflow` is a local-first Python SDK for developers who need resumable AI workflows without turning their scripts into a dashboard, SaaS, or observability platform.

It helps you:

- create local checkpoints per step;
- know which steps already completed;
- resume from the last valid state;
- hash inputs and outputs with SHA-256;
- export a `workflow_manifest.json`;
- detect when outputs have changed after issuance;
- issue a HREVN Verified Record when runtime credentials are configured.

The SDK is free to use locally. HREVN certification is available during the initial adoption phase to help developers generate verifiable workflow records without adding a separate pricing or provisioning step up front.

## Why this matters

If a workflow has 10 steps and fails at step 8, you should not need to rerun steps 1 to 7 blindly. This SDK gives you:

- clear step-level checkpoints
- deterministic resume behavior
- detection of changed or tampered outputs
- a manifest you can inspect and share

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

If you only want the package without test dependencies:

```bash
pip install -e .
```

## Five-minute quick start

```bash
python examples/basic_ai_pipeline.py
hrevn-workflow --storage-path examples/.hrevn status
hrevn-workflow --storage-path examples/.hrevn history
hrevn-workflow --storage-path examples/.hrevn telemetry-summary
hrevn-workflow --storage-path examples/.hrevn list-deliverables --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn doctor --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn manifest --path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn record-payload --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn inspect-step --step-id 04_issue_client_package
python examples/basic_ai_pipeline.py
```

What you should see:

- first run: steps execute;
- `status`: shows the last valid step and checkpoint hashes;
- `history`: shows the checkpoint chain in compact form;
- `telemetry-summary`: shows the local installation id, local event counts and certification state counts;
- `list-deliverables`: shows which files are currently certifiable;
- `doctor`: tells you quickly whether the workflow state is healthy;
- `manifest`: exports a workflow manifest;
- second run: previously valid steps are skipped.

## What this is not

This is not:

- a dashboard
- a hosted service
- a workflow engine
- enterprise observability

It is a small, local SDK for resumable workflows and verifiable outputs.

## Included examples

### 1. AI review pipeline

The bundled `basic_ai_pipeline.py` simulates a small AI review workflow:

1. source document
2. extracted text
3. LLM-style structured analysis mock
4. structured intake case JSON
5. client-facing review report
6. client packet metadata
7. exportable workflow manifest

Generated outputs:

- `examples/extracted_text.md`
- `examples/analysis.json`
- `examples/intake_case.json`
- `examples/client_review_report.md`
- `examples/client_packet.json`
- `examples/workflow_manifest.json`

### 2. Vendor due diligence pipeline

The bundled `vendor_due_diligence_pipeline.py` simulates a lightweight third-party AI review flow:

1. vendor brief
2. vendor summary
3. risk assessment JSON
4. follow-up questionnaire
5. due diligence memo
6. exportable workflow manifest

Generated outputs:

- `examples/vendor_summary.md`
- `examples/vendor_risk_assessment.json`
- `examples/vendor_follow_up_questions.md`
- `examples/vendor_due_diligence_memo.md`
- `examples/vendor_workflow_manifest.json`

## Minimal usage pattern

```python
from hrevn_workflow import Workflow

wf = Workflow(workflow_id="ai_review_pipeline_001", storage_path="./.hrevn")

with wf.step("01_extract_text", inputs=["input_document.txt"]) as step:
    if step.should_run():
        ...
        step.complete(outputs=["extracted_text.md"])

with wf.step("02_llm_analysis", inputs=["extracted_text.md"]) as step:
    if step.should_run():
        ...
        step.complete(outputs=["analysis.json"], model_used="gpt-4.1", tokens_in=12, tokens_out=4)

with wf.step("03_build_intake_case", inputs=["analysis.json"]) as step:
    if step.should_run():
        ...
        step.complete(outputs=["intake_case.json"], artifact_type="structured_case_json")

with wf.step("04_issue_client_package", inputs=["analysis.json", "intake_case.json"]) as step:
    if step.should_run():
        ...
        step.complete(
            outputs=["client_review_report.md", "client_packet.json"],
            report_type="markdown",
            delivery_mode="client_packet",
        )

print(wf.status())
print(wf.last_valid_step())
wf.export_manifest("workflow_manifest.json")
```

## What `.hrevn/` contains

```text
.hrevn/
  workflow_state.json
  checkpoints/
    01_extract_text.json
    02_llm_analysis.json
    03_build_intake_case.json
    04_issue_client_package.json
  manifests/
    workflow_manifest.json
```

Only metadata is stored there by default. Your actual outputs remain where your script writes them.

When integrated certification runs, the SDK also stores:

```text
.hrevn/
  certification/
    status.json
  telemetry/
    installation.json
    events.jsonl
```

Telemetry is intentionally minimal:

- the SDK keeps a stable local `installation_id`
- local workflow events are appended to `.hrevn/telemetry/events.jsonl`
- when HREVN certification is configured, that same installation identity is included in the certification request

There is no separate SaaS telemetry backend in this release. The main usage signal is still the certification path that already talks to HREVN when enabled.

Telemetry is local-only. No telemetry events are sent to HREVN unless you explicitly run certification, in which case the installation ID is included in the certification request.

## How resume works

If a step is already marked `completed` and its input metadata still matches, `should_run()` returns `False`. If the step failed before, does not exist yet, or the input metadata changed, `should_run()` returns `True`.

## Manifest export

`export_manifest()` writes a summary of the run, including:

- step chain;
- completed and failed counts;
- last valid step;
- certifiable deliverables derived from outputs.

After the manifest is written, the SDK also attempts integrated HREVN certification.

If HREVN runtime credentials are configured, the SDK stores:

- certification status
- bundle id
- record id
- download URL

If they are not configured, the SDK records:

- `status = not_configured`

without breaking the local workflow.

If credentials are configured but the remote certification call fails, the SDK records:

- `status = failed`

without invalidating the local workflow, the exported manifest, or the local integrity state.

The SDK also writes local telemetry events for:

- workflow initialization
- manifest export
- doctor runs
- certification state updates
- resets

These local events are meant for support, debugging and lightweight usage observation without changing the local-first nature of the SDK.

## Integrated certification

The certification path is built into the workflow lifecycle rather than exposed as a separate conceptual add-on.

Current behavior:

1. local workflow completes
2. manifest is exported
3. local integrity is verified
4. a Verified Record request is prepared
5. HREVN certification is attempted
6. certification result is stored locally

The important rule is this:

- local workflow completion remains valid on its own;
- manifest export remains valid on its own;
- remote certification failure does not invalidate the workflow;
- remote certification failure is recorded explicitly as certification state.

Required environment variables for live certification:

- `HREVN_API_BASE_URL`
- `HREVN_API_KEY`

Optional environment variables:

- `HREVN_WORKFLOW_AGENT_NAME`
- `HREVN_WORKFLOW_MODEL_VERSION`
- `HREVN_WORKFLOW_TEST_ENVIRONMENT`
- `HREVN_WORKFLOW_ISSUER_ID`
- `HREVN_WORKFLOW_ISSUER_NAME`
- `HREVN_WORKFLOW_ISSUER_TYPE`
- `HREVN_WORKFLOW_LICENSE_ID`
- `HREVN_WORKFLOW_INSTALLATION_ID`
- `HREVN_WORKFLOW_DISTRIBUTION_CHANNEL`
- `HREVN_WORKFLOW_DELIVERY_MODE`

For internal development and tests only:

- `HREVN_WORKFLOW_CERTIFY_MODE=disabled`

## HREVN Verified Record (optional)

When HREVN runtime credentials are configured, the SDK can generate a Verified Record that certifies:

- what was produced
- when it was produced
- which inputs were used
- whether the output has been modified

Learn more:

- [https://hrevn.com/en/verifiable-ai-records/](https://hrevn.com/en/verifiable-ai-records/)

## CLI

The package also includes a minimal CLI:

```bash
hrevn-workflow --storage-path examples/.hrevn status
hrevn-workflow --storage-path examples/.hrevn history
hrevn-workflow --storage-path examples/.hrevn list-deliverables --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn doctor --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn manifest --path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn reset --step-id 02_llm_analysis
hrevn-workflow --storage-path examples/.hrevn verify --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn record-payload --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn inspect-step --step-id 04_issue_client_package
```

Commands:

- `status`: prints the current workflow status as JSON;
- `history`: prints a compact checkpoint chain for the whole workflow;
- `list-deliverables`: prints the files currently exposed as certifiable deliverables;
- `doctor`: runs a quick health check on state, checkpoints, manifest and verification result;
- `doctor`: also reports certification status when available;
- `manifest`: exports and prints the current workflow manifest;
- `verify`: checks checkpoint integrity, input/output hashes and optional manifest consistency;
- `record-payload`: prepares the local payload that can later feed HREVN Verified Record, including the manifest and workflow deliverables;
- `inspect-step`: prints one checkpoint with its inputs, outputs, metrics and hash data;
- `reset`: clears all state or everything from a specific step onward.

## Repository hygiene

The repository is expected to stay local-first and lightweight:

- no API key required;
- no network dependency for the core flow;
- no dashboard or remote storage;
- generated example outputs and `.hrevn/` state stay out of version control.

## License

`hrevn-workflow` is released under the MIT License.

The local SDK is open source.
HREVN managed certification, runtime credentials, and backend services remain separate and may be subject to different terms.

## What it does not do

This MVP does **not**:

- upload files;
- create a dashboard;
- manage remote artifact storage;
- replace legal review;
- guarantee compliance;
- provide enterprise observability.

## Connection to HREVN Verified Record V1

The SDK includes `to_verified_record_payload()` as the local preparation layer behind integrated HREVN certification. It produces a payload that can certify:

- the workflow manifest itself;
- the workflow outputs listed as certifiable deliverables;
- the workflow summary and case reference needed for downstream verification.

In the current state of this repository:

- local integration logic is implemented
- remote certification is attempted automatically on manifest export
- live end-to-end certification has been validated against the real HREVN runtime
- minimal local telemetry is written under `.hrevn/telemetry/`

## Validation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
python examples/basic_ai_pipeline.py
hrevn-workflow --storage-path examples/.hrevn status
hrevn-workflow --storage-path examples/.hrevn history
hrevn-workflow --storage-path examples/.hrevn list-deliverables --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn doctor --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn manifest --path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn verify --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn record-payload --manifest-path examples/workflow_manifest.json
hrevn-workflow --storage-path examples/.hrevn inspect-step --step-id 04_issue_client_package
```

AI generates outputs.  
`hrevn-workflow` helps you resume and verify them.
python examples/basic_ai_pipeline.py
```

The second run should skip already valid steps.
