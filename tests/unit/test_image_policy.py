"""Política determinística de promoção de imagens da T03.3."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.delivery.image_policy import ImagePolicyError, evaluate_scan, load_policy

ROOT = Path(__file__).parent.parent.parent
POLICY_PATH = ROOT / "src" / "delivery" / "image_policy_v1.json"
FIXTURES = ROOT / "tests" / "fixtures" / "trivy"
IMAGE_DIGEST = "sha256:" + ("a" * 64)


def _scan(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_policy_schema_fixes_blocking_threshold_and_exception_ttl() -> None:
    policy = load_policy(POLICY_PATH)

    assert policy["schema_version"] == "1.0.0"
    assert policy["policy_id"] == "image-promotion-v1"
    assert policy["scanner"] == "trivy"
    assert policy["blocking_severities"] == ["CRITICAL", "HIGH"]
    assert policy["only_when_fix_available"] is True
    assert policy["exception_max_days"] == 30
    assert policy["exceptions"] == []


def test_clean_scan_passes_and_preserves_digest() -> None:
    result = evaluate_scan(
        scan=_scan("clean.json"),
        policy=load_policy(POLICY_PATH),
        image_digest=IMAGE_DIGEST,
        evaluated_on=date(2026, 8, 12),
    )

    assert result["decision"] == "pass"
    assert result["image_digest"] == IMAGE_DIGEST
    assert result["blocking_findings"] == []


@pytest.mark.parametrize("fixture", ["high-fixable.json", "critical-fixable.json"])
def test_fixable_high_or_critical_blocks_promotion(fixture: str) -> None:
    result = evaluate_scan(
        scan=_scan(fixture),
        policy=load_policy(POLICY_PATH),
        image_digest=IMAGE_DIGEST,
        evaluated_on=date(2026, 8, 12),
    )

    assert result["decision"] == "block"
    assert len(result["blocking_findings"]) == 1
    assert result["blocking_findings"][0]["fixed_version"]


def test_unfixed_high_is_reported_but_does_not_block() -> None:
    result = evaluate_scan(
        scan=_scan("high-unfixed.json"),
        policy=load_policy(POLICY_PATH),
        image_digest=IMAGE_DIGEST,
        evaluated_on=date(2026, 8, 12),
    )

    assert result["decision"] == "pass"
    assert result["blocking_findings"] == []
    assert result["non_blocking_findings"][0]["vulnerability_id"] == "CVE-TEST-UNFIXED"


def test_exception_requires_owner_reason_and_at_most_30_days() -> None:
    policy = load_policy(POLICY_PATH)
    policy["exceptions"] = [
        {
            "vulnerability_id": "CVE-TEST-HIGH",
            "image": "usiedu-api",
            "owner": "security-team",
            "reason": "Mitigação de runtime validada enquanto a atualização é testada.",
            "created_on": "2026-08-12",
            "expires_on": "2026-09-11",
        }
    ]

    result = evaluate_scan(
        scan=_scan("high-fixable.json"),
        policy=policy,
        image_digest=IMAGE_DIGEST,
        image_name="usiedu-api",
        evaluated_on=date(2026, 8, 20),
    )
    assert result["decision"] == "pass"
    assert result["accepted_exceptions"][0]["vulnerability_id"] == "CVE-TEST-HIGH"

    policy["exceptions"][0]["expires_on"] = "2026-09-12"
    with pytest.raises(ImagePolicyError, match="30 dias"):
        evaluate_scan(
            scan=_scan("high-fixable.json"),
            policy=policy,
            image_digest=IMAGE_DIGEST,
            image_name="usiedu-api",
            evaluated_on=date(2026, 8, 20),
        )


@pytest.mark.parametrize(
    "digest",
    ["latest", "sha256:abc", "sha256:" + ("g" * 64), "a" * 64],
)
def test_digest_must_be_immutable_sha256(digest: str) -> None:
    with pytest.raises(ImagePolicyError, match="digest"):
        evaluate_scan(
            scan=_scan("clean.json"),
            policy=load_policy(POLICY_PATH),
            image_digest=digest,
            evaluated_on=date(2026, 8, 12),
        )
