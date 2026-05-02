from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CertificationSettings:
    mode: str
    api_base_url: str | None
    api_key: str | None
    agent_name: str
    model_version: str
    test_environment: str
    issuer_id: str
    issuer_name: str
    issuer_type: str
    distribution_channel: str
    delivery_mode: str
    license_id: str | None
    installation_id: str | None


def load_certification_settings() -> CertificationSettings:
    return CertificationSettings(
        mode=os.getenv("HREVN_WORKFLOW_CERTIFY_MODE", "auto").strip().lower() or "auto",
        api_base_url=(os.getenv("HREVN_API_BASE_URL") or "").strip() or None,
        api_key=(os.getenv("HREVN_API_KEY") or "").strip() or None,
        agent_name=os.getenv("HREVN_WORKFLOW_AGENT_NAME", "HREVN Workflow SDK").strip(),
        model_version=os.getenv("HREVN_WORKFLOW_MODEL_VERSION", "workflow-sdk-v0.1").strip(),
        test_environment=os.getenv("HREVN_WORKFLOW_TEST_ENVIRONMENT", "local").strip(),
        issuer_id=os.getenv("HREVN_WORKFLOW_ISSUER_ID", "hrevn").strip(),
        issuer_name=os.getenv("HREVN_WORKFLOW_ISSUER_NAME", "HREVN").strip(),
        issuer_type=os.getenv("HREVN_WORKFLOW_ISSUER_TYPE", "organizational_issuer").strip(),
        distribution_channel=os.getenv("HREVN_WORKFLOW_DISTRIBUTION_CHANNEL", "sdk-integrated").strip(),
        delivery_mode=os.getenv("HREVN_WORKFLOW_DELIVERY_MODE", "sdk").strip(),
        license_id=(os.getenv("HREVN_WORKFLOW_LICENSE_ID") or "").strip() or None,
        installation_id=(os.getenv("HREVN_WORKFLOW_INSTALLATION_ID") or "").strip() or None,
    )
