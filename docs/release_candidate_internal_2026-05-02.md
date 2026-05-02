# hrevn-workflow

## Internal Release Candidate

Date: `2026-05-02`  
Version: `0.1.0`  
Status: `internal release candidate`

## Summary

`hrevn-workflow` is now in a strong internal state as a local-first SDK for resumable AI workflows.

It already supports:

- local checkpoints per step in `.hrevn/`
- resume-from-last-valid-step behavior
- SHA-256 hashing of inputs and outputs
- checkpoint chaining with `previous_checkpoint_hash`
- `workflow_manifest.json` export
- local integrity verification
- local `Verified Record` payload preparation
- integrated remote certification attempt on manifest export
- CLI inspection and diagnosis

This is no longer just a technical prototype. It is a usable internal product candidate.

## What the current release candidate does

Core workflow features:

- `Workflow.step(...)`
- `should_run()`
- `complete()`
- `fail()`
- `skip()`
- `reset()`

Manifest and verification features:

- `export_manifest()`
- `verify()`
- `doctor()`
- `to_verified_record_payload()`
- integrated certification status persistence

CLI features:

- `hrevn-workflow status`
- `hrevn-workflow history`
- `hrevn-workflow list-deliverables`
- `hrevn-workflow inspect-step --step-id ...`
- `hrevn-workflow manifest`
- `hrevn-workflow verify`
- `hrevn-workflow doctor`
- `hrevn-workflow record-payload`
- `hrevn-workflow reset`

## What the example currently demonstrates

The bundled example is no longer a trivial toy flow. It simulates a small AI review pipeline:

1. source document
2. extracted text
3. structured LLM-style analysis mock
4. structured intake case JSON
5. client-facing review report
6. client packet metadata
7. manifest export

Generated example outputs:

- `examples/extracted_text.md`
- `examples/analysis.json`
- `examples/intake_case.json`
- `examples/client_review_report.md`
- `examples/client_packet.json`
- `examples/workflow_manifest.json`

## Verified behaviors

The following behaviors have been verified in tests and real command runs:

- first execution runs all pending steps
- second execution skips valid completed steps
- changing an input forces rerun of the affected step
- step exceptions create failed checkpoints
- manifest export reflects the current checkpoint chain
- `verify` detects output tampering
- `doctor` reports workflow health and integrity state
- `record-payload` includes the manifest and workflow deliverables
- `record-payload` refuses to emit when integrity checks fail
- integrated certification records `not_configured` when runtime credentials are absent
- integrated certification records `generated` when the remote runtime is mocked successfully
- integrated certification can record `failed` when the remote call fails after local workflow completion
- remote certification failure does not invalidate the local workflow or its exported manifest
- integrated certification has been validated live against `https://api.hrevn.com`
- a real `Verified Record` response has been persisted locally with `bundle_id`, `record_id` and `download_url`

## Current acceptance criteria

This release candidate should be considered healthy only if all of the following remain true:

- local installation works with `pip install -e '.[dev]'`
- CLI commands work without API keys
- `pytest -q` is green
- example pipeline runs successfully from zero state
- second example run skips already valid steps
- tampering after manifest export is detected
- `record-payload` fails on tampered state
- integrated certification writes a local certification status record
- live certification can complete successfully when valid HREVN runtime credentials are present
- remote certification failure is acceptable if it is recorded explicitly and the local workflow remains healthy

## Validation commands

### Test suite

```bash
cd hrevn-workflow
pytest -q
```

Last validated result:

- `25 passed`

### Clean-environment publication smoke

Validated in a copied repo under a fresh temporary virtual environment.

Important nuance:

- in this no-network sandbox, `pip install -e '.[dev]'` tried build isolation and failed while fetching `setuptools>=68`
- the package itself was validated successfully with:

```bash
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install --no-build-isolation -e '.[dev]'
pytest -q
python examples/basic_ai_pipeline.py
python -m hrevn_workflow.cli --storage-path examples/.hrevn manifest --path examples/workflow_manifest.json
python -m hrevn_workflow.cli --storage-path examples/.hrevn doctor --manifest-path examples/workflow_manifest.json
python examples/vendor_due_diligence_pipeline.py
```

Observed result:

- install: OK
- tests: OK
- AI review example: OK
- vendor due diligence example: OK
- `doctor`: `ok = true`
- integrated certification state persisted locally

### Live certification validation

Validated against the real HREVN managed service runtime using valid server credentials.

Observed result:

- certification status: `generated`
- certification ok: `true`
- `bundle_id = BND-C2F36E121AD9`
- `record_id = AER-6E121AD9`
- `download_url = /v1/bundles/BND-C2F36E121AD9/download`
- `expires_at = 2026-05-03T11:34:53Z`

This confirms that the integrated certification path is no longer just implemented or mocked. It has been exercised end-to-end against the live HREVN runtime and persisted correctly into `.hrevn/certification/status.json`.

### Normal example flow

```bash
python3 -c "from pathlib import Path; from hrevn_workflow import Workflow; Workflow('ai_review_pipeline_001', storage_path=Path('examples/.hrevn'), project='examples').reset()"
python3 examples/basic_ai_pipeline.py
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn status
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn history
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn list-deliverables --manifest-path examples/workflow_manifest.json
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn manifest --path examples/workflow_manifest.json
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn verify --manifest-path examples/workflow_manifest.json
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn doctor --manifest-path examples/workflow_manifest.json
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn record-payload --manifest-path examples/workflow_manifest.json
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn inspect-step --step-id 04_issue_client_package
python3 examples/basic_ai_pipeline.py
```

Expected:

- first run: `executed`
- second run: `skipped`
- `verify`: `ok = true`
- `doctor`: `ok = true`
- certification status: `not_configured` unless runtime credentials are present
- with valid runtime credentials, certification status: `generated`

### Vendor example flow

```bash
python3 -c "from pathlib import Path; from hrevn_workflow import Workflow; Workflow('vendor_due_diligence_001', storage_path=Path('examples/.hrevn_vendor'), project='examples').reset()"
python3 examples/vendor_due_diligence_pipeline.py
```

Expected:

- the 4 steps execute
- `last_valid_step = 04_issue_due_diligence_memo`
- `vendor_workflow_manifest.json` is generated

### Tampering scenario

```bash
python3 -c "from pathlib import Path; from hrevn_workflow import Workflow; Workflow('ai_review_pipeline_001', storage_path=Path('examples/.hrevn'), project='examples').reset()"
python3 examples/basic_ai_pipeline.py
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn manifest --path examples/workflow_manifest.json
python3 -c "from pathlib import Path; p=Path('examples/client_review_report.md'); p.write_text(p.read_text(encoding='utf-8') + '\nTampered after manifest.\n', encoding='utf-8')"
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn doctor --manifest-path examples/workflow_manifest.json
python3 -m hrevn_workflow.cli --storage-path examples/.hrevn record-payload --manifest-path examples/workflow_manifest.json
```

Expected:

- `doctor`: `ok = false`
- `issues_count >= 1`
- `record-payload`: fails with integrity error

## What this release candidate is not

This release candidate does **not** yet try to be:

- a hosted service
- a dashboard
- a remote artifact manager
- a workflow orchestrator
- a compliance engine

It is still intentionally:

- local-first
- small
- explicit
- inspectable
- network-free in the core flow

## Remaining gaps before public GitHub

These are the main gaps still open before public publication is sensible:

1. repository should be reviewed one last time for public-facing polish
2. we should decide whether public release happens GitHub-only first or after a later PyPI pass
3. we should decide how prominently to frame integrated HREVN certification in the first public release

## Recommendation

This release candidate is now technically strong enough to support a public GitHub release if we want one.

The correct next use of this release candidate is:

1. do one last public-facing surface review
2. decide the publication framing: GitHub-only first or broader release
3. publish only once we are happy with that framing and repo presentation

## Release judgement

Current judgement:

- product minimum: `yes`
- internally demonstrable: `yes`
- internally verifiable: `yes`
- internally integrated with remote certification path: `yes`
- live HREVN certification validated: `yes`
- public GitHub ready: `yes`
