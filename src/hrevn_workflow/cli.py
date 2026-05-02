from __future__ import annotations

import argparse
import json
import sys

from .errors import WorkflowError
from .workflow import Workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hrevn-workflow",
        description="Local workflow checkpoints for resumable AI pipelines.",
    )
    parser.add_argument(
        "--storage-path",
        default="./.hrevn",
        help="Path to the local .hrevn state directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show workflow status from local state.")
    subparsers.add_parser("history", help="Show a compact history of workflow checkpoints.")
    subparsers.add_parser("telemetry-summary", help="Show a compact summary of local telemetry events.")
    doctor_parser = subparsers.add_parser("doctor", help="Run a quick health check on local workflow state.")
    doctor_parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional manifest path to validate. Defaults to .hrevn/manifests/workflow_manifest.json if present.",
    )

    manifest_parser = subparsers.add_parser("manifest", help="Export workflow manifest.")
    manifest_parser.add_argument(
        "--path",
        default=None,
        help="Optional output path for workflow_manifest.json.",
    )

    deliverables_parser = subparsers.add_parser(
        "list-deliverables",
        help="List workflow deliverables that are currently certifiable.",
    )
    deliverables_parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional manifest path to use. Defaults to .hrevn/manifests/workflow_manifest.json if present.",
    )

    verify_parser = subparsers.add_parser("verify", help="Verify workflow checkpoints and manifest consistency.")
    verify_parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional manifest path to verify. Defaults to .hrevn/manifests/workflow_manifest.json if present.",
    )

    record_payload_parser = subparsers.add_parser(
        "record-payload",
        help="Build a local Verified Record payload from the workflow manifest.",
    )
    record_payload_parser.add_argument(
        "--manifest-path",
        default=None,
        help="Optional manifest path to use. Defaults to .hrevn/manifests/workflow_manifest.json if present.",
    )

    inspect_parser = subparsers.add_parser(
        "inspect-step",
        help="Inspect a specific checkpoint step with inputs, outputs and metrics.",
    )
    inspect_parser.add_argument(
        "--step-id",
        required=True,
        help="Step id to inspect.",
    )

    reset_parser = subparsers.add_parser("reset", help="Reset all state or from a specific step.")
    reset_parser.add_argument(
        "--step-id",
        default=None,
        help="Optional step id from which state should be cleared.",
    )

    return parser


def load_workflow(storage_path: str) -> Workflow:
    return Workflow.from_storage(storage_path=storage_path)


def command_status(storage_path: str) -> int:
    workflow = load_workflow(storage_path)
    print(json.dumps(workflow.status(), indent=2, ensure_ascii=False))
    return 0


def command_history(storage_path: str) -> int:
    workflow = load_workflow(storage_path)
    print(json.dumps(workflow.history(), indent=2, ensure_ascii=False))
    return 0


def command_telemetry_summary(storage_path: str) -> int:
    workflow = load_workflow(storage_path)
    print(json.dumps(workflow.telemetry_summary(), indent=2, ensure_ascii=False))
    return 0


def command_doctor(storage_path: str, manifest_path: str | None) -> int:
    workflow = load_workflow(storage_path)
    print(json.dumps(workflow.doctor(manifest_path=manifest_path), indent=2, ensure_ascii=False))
    return 0


def command_manifest(storage_path: str, path: str | None) -> int:
    workflow = load_workflow(storage_path)
    manifest = workflow.export_manifest(path)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def command_list_deliverables(storage_path: str, manifest_path: str | None) -> int:
    workflow = load_workflow(storage_path)
    payload = workflow.list_deliverables(manifest_path=manifest_path)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_verify(storage_path: str, manifest_path: str | None) -> int:
    workflow = load_workflow(storage_path)
    result = workflow.verify(manifest_path=manifest_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def command_record_payload(storage_path: str, manifest_path: str | None) -> int:
    workflow = load_workflow(storage_path)
    payload = workflow.to_verified_record_payload(manifest_path=manifest_path)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_inspect_step(storage_path: str, step_id: str) -> int:
    workflow = load_workflow(storage_path)
    payload = workflow.inspect_step(step_id)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_reset(storage_path: str, step_id: str | None) -> int:
    workflow = load_workflow(storage_path)
    workflow.reset(step_id=step_id)
    target = f"from step {step_id}" if step_id else "completely"
    print(f"Workflow state reset {target}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            return command_status(args.storage_path)
        if args.command == "history":
            return command_history(args.storage_path)
        if args.command == "telemetry-summary":
            return command_telemetry_summary(args.storage_path)
        if args.command == "doctor":
            return command_doctor(args.storage_path, args.manifest_path)
        if args.command == "manifest":
            return command_manifest(args.storage_path, args.path)
        if args.command == "list-deliverables":
            return command_list_deliverables(args.storage_path, args.manifest_path)
        if args.command == "verify":
            return command_verify(args.storage_path, args.manifest_path)
        if args.command == "record-payload":
            return command_record_payload(args.storage_path, args.manifest_path)
        if args.command == "inspect-step":
            return command_inspect_step(args.storage_path, args.step_id)
        if args.command == "reset":
            return command_reset(args.storage_path, args.step_id)
    except (FileNotFoundError, WorkflowError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
