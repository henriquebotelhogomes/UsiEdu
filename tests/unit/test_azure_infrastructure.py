"""Regression checks for Azure Container Apps resource sizing."""

from pathlib import Path


def test_api_container_uses_a_valid_4_gib_consumption_profile() -> None:
    """Four GiB in Consumption requires the corresponding two-vCPU profile."""
    bicep = (Path(__file__).parents[2] / "infra" / "azure" / "main.bicep").read_text(
        encoding="utf-8"
    )
    api_section = bicep.split("resource apiApp", maxsplit=1)[1].split(
        "resource frontendApp", maxsplit=1
    )[0]

    assert "cpu: json('2.0')" in api_section
    assert "memory: '4Gi'" in api_section
