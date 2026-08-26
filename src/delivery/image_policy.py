"""Avalia relatórios JSON do Trivy antes da promoção de uma imagem."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SEVERITIES = {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


class ImagePolicyError(ValueError):
    """Indica política, relatório ou referência de imagem inválida."""


def load_policy(path: Path) -> dict[str, Any]:
    """Carrega e valida a política versionada."""
    policy = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "policy_id",
        "scanner",
        "blocking_severities",
        "only_when_fix_available",
        "exception_max_days",
        "exceptions",
    }
    missing = required - policy.keys()
    if missing:
        raise ImagePolicyError(f"Política sem campos obrigatórios: {sorted(missing)}")
    if policy["schema_version"] != "1.0.0":
        raise ImagePolicyError("schema_version de política não suportado")
    if policy["scanner"] != "trivy":
        raise ImagePolicyError("scanner deve ser trivy")
    if not isinstance(policy["blocking_severities"], list) or not set(
        policy["blocking_severities"]
    ).issubset(SEVERITIES):
        raise ImagePolicyError("blocking_severities inválido")
    if not isinstance(policy["only_when_fix_available"], bool):
        raise ImagePolicyError("only_when_fix_available deve ser booleano")
    if (
        not isinstance(policy["exception_max_days"], int)
        or isinstance(policy["exception_max_days"], bool)
        or policy["exception_max_days"] < 1
        or policy["exception_max_days"] > 30
    ):
        raise ImagePolicyError("exception_max_days deve estar entre 1 e 30")
    if not isinstance(policy["exceptions"], list):
        raise ImagePolicyError("exceptions deve ser uma lista")
    return policy


def _validated_exceptions(policy: dict[str, Any]) -> list[dict[str, Any]]:
    required = {
        "vulnerability_id",
        "image",
        "owner",
        "reason",
        "created_on",
        "expires_on",
    }
    validated = []
    for exception in policy["exceptions"]:
        if not isinstance(exception, dict) or required - exception.keys():
            raise ImagePolicyError("Exceção sem campos obrigatórios")
        for field in ("vulnerability_id", "image", "owner", "reason"):
            if not isinstance(exception[field], str) or not exception[field].strip():
                raise ImagePolicyError(f"Exceção exige {field} não vazio")
        try:
            created_on = date.fromisoformat(exception["created_on"])
            expires_on = date.fromisoformat(exception["expires_on"])
        except (TypeError, ValueError) as exc:
            raise ImagePolicyError("Datas da exceção devem usar ISO 8601") from exc
        duration = (expires_on - created_on).days
        if duration < 0 or duration > policy["exception_max_days"]:
            raise ImagePolicyError("Exceção deve ter validade máxima de 30 dias")
        validated.append({**exception, "_expires_on": expires_on})
    return validated


def _findings(scan: dict[str, Any]) -> list[dict[str, str]]:
    if scan.get("SchemaVersion") != 2 or not isinstance(scan.get("Results"), list):
        raise ImagePolicyError("Relatório Trivy JSON schema 2 inválido")
    findings = []
    for result in scan["Results"]:
        vulnerabilities = result.get("Vulnerabilities") or []
        if not isinstance(vulnerabilities, list):
            raise ImagePolicyError("Vulnerabilities deve ser uma lista")
        for vulnerability in vulnerabilities:
            severity = vulnerability.get("Severity")
            if severity not in SEVERITIES:
                raise ImagePolicyError(f"Severidade Trivy inválida: {severity!r}")
            vulnerability_id = vulnerability.get("VulnerabilityID")
            if not isinstance(vulnerability_id, str) or not vulnerability_id:
                raise ImagePolicyError("VulnerabilityID obrigatório")
            findings.append(
                {
                    "vulnerability_id": vulnerability_id,
                    "package": str(vulnerability.get("PkgName", "")),
                    "installed_version": str(vulnerability.get("InstalledVersion", "")),
                    "fixed_version": str(vulnerability.get("FixedVersion", "")),
                    "severity": severity,
                    "target": str(result.get("Target", "")),
                }
            )
    return findings


def evaluate_scan(
    *,
    scan: dict[str, Any],
    policy: dict[str, Any],
    image_digest: str,
    evaluated_on: date,
    image_name: str | None = None,
) -> dict[str, Any]:
    """Produz uma decisão reproduzível para um relatório Trivy e digest."""
    if not DIGEST_PATTERN.fullmatch(image_digest):
        raise ImagePolicyError("image_digest deve ser um digest sha256 imutável")
    exceptions = _validated_exceptions(policy)
    findings = _findings(scan)
    resolved_image_name = image_name or str(scan.get("ArtifactName", ""))
    blocking = []
    non_blocking = []
    accepted = []

    for finding in findings:
        severity_blocks = finding["severity"] in policy["blocking_severities"]
        fix_blocks = bool(finding["fixed_version"]) or not policy["only_when_fix_available"]
        if not (severity_blocks and fix_blocks):
            non_blocking.append(finding)
            continue

        matching_exception = next(
            (
                exception
                for exception in exceptions
                if exception["vulnerability_id"] == finding["vulnerability_id"]
                and exception["image"] == resolved_image_name
                and evaluated_on <= exception["_expires_on"]
            ),
            None,
        )
        if matching_exception:
            accepted.append(
                {key: value for key, value in matching_exception.items() if key != "_expires_on"}
            )
        else:
            blocking.append(finding)

    return {
        "schema_version": "1.0.0",
        "policy_id": policy["policy_id"],
        "scanner": "trivy",
        "evaluated_on": evaluated_on.isoformat(),
        "image_name": resolved_image_name,
        "image_digest": image_digest,
        "decision": "block" if blocking else "pass",
        "blocking_findings": blocking,
        "non_blocking_findings": non_blocking,
        "accepted_exceptions": accepted,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--image")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = evaluate_scan(
        scan=json.loads(args.scan.read_text(encoding="utf-8")),
        policy=load_policy(args.policy),
        image_digest=args.digest,
        image_name=args.image,
        evaluated_on=args.date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    raise SystemExit(1 if result["decision"] == "block" else 0)


if __name__ == "__main__":
    main()
