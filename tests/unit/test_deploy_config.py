"""Testes da configuração necessária ao deploy público (T9.4)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def test_cors_origins_uses_configured_single_public_origin(monkeypatch) -> None:
    """O deploy aceita apenas a origem pública configurada, nunca wildcard."""
    monkeypatch.setenv("USIEDU_CORS_ORIGINS", "https://usiedu.example.com")

    from src.api.main import get_cors_origins

    assert get_cors_origins() == ["https://usiedu.example.com"]


def test_cors_origins_supports_local_development_origins(monkeypatch) -> None:
    """O ambiente local continua aceitando as duas portas usadas pelo Vite."""
    monkeypatch.delenv("USIEDU_CORS_ORIGINS", raising=False)

    from src.api.main import get_cors_origins

    assert get_cors_origins() == ["http://localhost:5173", "http://localhost:5174"]


def test_auth_uses_documented_jwt_secret(monkeypatch) -> None:
    """A variável documentada JWT_SECRET assina os tokens do ambiente público."""
    monkeypatch.setenv("JWT_SECRET", "segredo-do-deploy")
    monkeypatch.delenv("USIEDU_JWT_SECRET", raising=False)

    from src.api.auth import get_secret_key

    assert get_secret_key() == "segredo-do-deploy"


def test_capture_screenshots_accepts_public_base_url() -> None:
    """As capturas podem apontar para o frontend HTTPS já publicado."""
    script_path = Path("scripts/capture_screenshots.py")
    spec = importlib.util.spec_from_file_location("capture_screenshots", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    args = module.parse_args(["--base-url", "https://usiedu.example.com/"])

    assert args.base_url == "https://usiedu.example.com"


def test_azure_bicep_declares_public_stack_and_ingest_job() -> None:
    """O deploy declara frontend, API, Qdrant persistente e job de ingestão."""
    template = Path("infra/azure/main.bicep")
    assert template.is_file(), "O template Bicep de Azure Container Apps deve existir."

    content = template.read_text(encoding="utf-8")
    for resource_name in ("frontendApp", "apiApp", "qdrantApp", "ingestJob"):
        assert f"resource {resource_name}" in content


def test_azure_deploy_expands_acr_credentials_in_powershell() -> None:
    """O script deve expandir as propriedades das credenciais antes do deploy."""
    script = Path("infra/azure/deploy.ps1").read_text(encoding="utf-8")

    assert "registryUsername=$($registryCredentials.username)" in script
    assert "registryPassword=$($registryCredentials.password)" in script


def test_azure_deploy_does_not_report_success_after_arm_failure() -> None:
    """Uma falha ARM deve interromper o script antes das instrucoes finais."""
    script = Path("infra/azure/deploy.ps1").read_text(encoding="utf-8")

    assert "$deploymentJson = az deployment group create" in script
    assert "if ($LASTEXITCODE -ne 0)" in script


def test_azure_ingest_job_has_memory_for_embedding_model() -> None:
    """O job de ingestao precisa suportar o carregamento do modelo de embeddings."""
    content = Path("infra/azure/main.bicep").read_text(encoding="utf-8")
    ingest_job = content.split("resource ingestJob", maxsplit=1)[1]

    assert "cpu: json('1.0')" in ingest_job
    assert "memory: '2Gi'" in ingest_job


def test_azure_qdrant_urls_use_container_app_service_discovery() -> None:
    """API e ingestao acessam Qdrant pelo nome curto do Container App."""
    content = Path("infra/azure/main.bicep").read_text(encoding="utf-8")

    assert content.count("value: 'http://${qdrantApp.name}'") == 2


def test_dockerignore_excludes_local_runtime_data_from_build_context() -> None:
    """Imagens não enviam Qdrant, bancos ou segredos locais ao daemon Docker."""
    dockerignore = Path(".dockerignore")
    assert dockerignore.is_file(), "O contexto Docker precisa de um .dockerignore."

    patterns = set(dockerignore.read_text(encoding="utf-8").splitlines())
    assert {"qdrant_storage/", "*.db", ".env", ".git/"} <= patterns


def test_api_dockerfile_copies_package_before_installing_it() -> None:
    """O Hatchling precisa de src/ no builder para criar os metadados do pacote."""
    dockerfile = Path("Dockerfile.api").read_text(encoding="utf-8")

    assert dockerfile.index("COPY src/ ./src/") < dockerfile.index("pip install --no-cache-dir .")


def test_hatchling_build_includes_src_package() -> None:
    """A imagem instala o projeto a partir de src/, não de um pacote inexistente usiedu/."""
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.hatch.build.targets.wheel]" in pyproject
    assert 'packages = ["src"]' in pyproject
