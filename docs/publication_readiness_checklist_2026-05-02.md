# hrevn-workflow

## Publication Readiness Checklist

Date: `2026-05-02`  
Version reviewed: `0.1.0`  
Decision scope: `Should this SDK be published to a public GitHub repository now?`

## Current decision

Current answer:

- `Yes, for a public GitHub repository`

Reason:

- the product minimum is strong
- internal validation is strong
- integrated HREVN certification is now validated end-to-end against the live runtime
- the remaining open questions are publication framing and release surface, not core product viability

This is a **release-readiness checklist**, not a technical ambition list.

## Readiness checklist

### 1. Core product behavior

- `YES` local-first workflow execution works
- `YES` checkpoint persistence works
- `YES` resume behavior works
- `YES` reset behavior works
- `YES` manifest export works
- `YES` integrity verification works
- `YES` tampering detection works
- `YES` `record-payload` refuses integrity-broken state
- `YES` integrated certification status is persisted locally
- `YES` remote certification path is implemented and test-covered
- `YES` live remote certification against real HREVN credentials is confirmed

Judgement:

- core behavior is strong enough

### 2. CLI usability

- `YES` `status`
- `YES` `history`
- `YES` `inspect-step`
- `YES` `list-deliverables`
- `YES` `manifest`
- `YES` `verify`
- `YES` `doctor`
- `YES` `record-payload`
- `YES` `reset`

Judgement:

- CLI coverage is already good for an internal developer preview

### 3. Example coverage

- `YES` AI review example exists
- `YES` vendor due diligence example exists
- `YES` examples generate real output files
- `YES` examples generate manifests
- `YES` examples are useful to demonstrate value
- `YES` examples have been re-run in a clean external-style environment
- `YES` integrated certification has been confirmed live from the example flow

Judgement:

- examples are good enough in content
- external installation proof is good enough for GitHub publication

### 4. Documentation

- `YES` README explains the product clearly
- `YES` README contains installation
- `YES` README contains quick start
- `YES` README documents the CLI
- `YES` README explains `.hrevn/`
- `YES` README explains `Verified Record` connection
- `YES` README has received a final public-facing polish pass for developer tone and brevity
- `PENDING` decide whether the public README should lead with local-first workflow value or more prominently with integrated HREVN certification

Judgement:

- docs are strong enough for publication
- one framing decision remains about how prominently to lead with HREVN certification

### 5. Testing and verification

- `YES` automated tests exist
- `YES` normal success flow is covered
- `YES` rerun/skip behavior is covered
- `YES` failure behavior is covered
- `YES` tampering behavior is covered
- `YES` CLI behavior is covered
- `YES` doctor/verify/record-payload integrity path is covered

Last validated suite result:

- `25 passed`

Judgement:

- test coverage is strong for the current scope

### 6. Packaging and installability

- `YES` package entrypoint exists
- `YES` `pyproject.toml` is present
- `YES` editable install path exists
- `YES` version is defined
- `YES` license file is present
- `YES` install has been validated once more from a clean copied environment
- `PENDING` we should decide whether publication path is GitHub-only first or PyPI later

Judgement:

- packaging is strong
- installability is good internally
- one nuance remains: in a no-network sandbox, build isolation requires `--no-build-isolation`

### 7. Product boundaries

- `YES` the SDK remains local-first
- `YES` local workflow use does not require an API key
- `NO` full integrated HREVN certification currently requires runtime credentials
- `YES` no dashboard is required
- `NO` the integrated certification path now depends on a remote HREVN backend
- `YES` remote certification failure does not invalidate a healthy local workflow or manifest
- `YES` no orchestration complexity has been introduced
- `YES` the product is still explainable in under 10 minutes

Judgement:

- the product has stayed on the right side of simplicity, but it is no longer purely local if HREVN certification is part of the promise
- the failure boundary is correct: remote certification can fail without breaking the local workflow result

## What is already strong enough

These parts no longer look like blockers:

- core SDK design
- workflow checkpoints
- local verification
- CLI usefulness
- product framing
- two realistic examples
- internal confidence in behavior
- integrated certification architecture
- live integrated certification validation

## What still blocks public GitHub

These are the real blockers now:

1. final decision on GitHub-only first or PyPI later
2. final decision on how prominently to frame integrated HREVN certification in the public README and repo positioning

These are not architecture blockers. They are **publication-quality blockers**.

## What should not block publication

The following should **not** delay publication if the blockers above are closed:

- no dashboard
- no SaaS layer
- no branching DAGs
- no plugins
- no cloud execution

Those are future-product questions, not release blockers for this SDK.

## Release judgement matrix

### Product minimum

- `YES`

### Internally demonstrable

- `YES`

### Internally verifiable

- `YES`

### Public GitHub ready today

- `YES`

### Public GitHub ready after one short productization pass

- `YES`

## Recommended next sequence

1. review repository surface for public visibility
2. decide GitHub-only first or PyPI later
3. decide public framing for integrated HREVN certification
4. make publication decision

## Final recommendation

Recommendation today:

- GitHub publication is now technically reasonable
- PyPI publication still deserves a separate packaging decision

Recommendation after the short final pass:

- `yes`, once the publication framing decisions above are closed

This is important:

the product no longer looks conceptually weak.  
It now looks ready enough for GitHub, with the remaining work being presentational and release-strategy decisions rather than core validation.
