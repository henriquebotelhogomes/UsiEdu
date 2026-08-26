"""Testes da configuração necessária ao deploy público (T9.4)."""

from __future__ import annotations

import builtins
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


def test_capture_screenshots_accepts_public_base_url_without_playwright(monkeypatch) -> None:
    """O parser do script não exige a dependência opcional Playwright."""
    original_import = builtins.__import__

    def block_playwright_import(name: str, *args, **kwargs):
        if name == "playwright" or name.startswith("playwright."):
            raise ModuleNotFoundError("No module named 'playwright'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_playwright_import)
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


def test_azure_deploy_supports_ghcr_images() -> None:
    """O script de deploy publica as imagens para o GHCR com usuário GitHub configurável."""
    script = Path("infra/azure/deploy.ps1").read_text(encoding="utf-8")

    assert "$apiImage = \"ghcr.io/$($GitHubUser.ToLower())/usiedu-api:$ImageTag\"" in script
    expected_frontend = (
        "$frontendImage = \"ghcr.io/$($GitHubUser.ToLower())/usiedu-frontend:$ImageTag\""
    )
    assert expected_frontend in script


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
    """Qdrant usa a porta HTTP do proxy interno, nao a porta do container."""
    content = Path("infra/azure/main.bicep").read_text(encoding="utf-8")

    assert content.count("value: 'http://${qdrantApp.name}:80'") == 2


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


def test_azure_api_declares_shallow_liveness_and_readiness_probes() -> None:
    template = Path("infra/azure/main.bicep").read_text(encoding="utf-8")
    api_app = template.split("resource apiApp", maxsplit=1)[1].split(
        "resource frontendApp", maxsplit=1
    )[0]

    assert "type: 'Liveness'" in api_app
    assert "type: 'Readiness'" in api_app
    assert "path: '/health'" in api_app
    assert "path: '/ready'" in api_app
    assert "port: 8000" in api_app


def test_api_image_installs_trivy_remediated_python_dependencies() -> None:
    """A imagem da API não deve reintroduzir achados HIGH corrigíveis do Trivy."""
    dockerfile = Path("Dockerfile.api").read_text(encoding="utf-8")
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "setuptools>=78.1.1" in dockerfile
    assert '"msgpack>=1.2.1"' in pyproject
    assert "pip/_vendor/bom.cdx.json" in dockerfile


def test_api_image_applies_security_updates_in_builder_and_runtime() -> None:
    """Pacotes Debian com correção disponível devem ser atualizados antes do scan."""
    dockerfile = Path("Dockerfile.api").read_text(encoding="utf-8")

    assert dockerfile.count("apt-get upgrade -y") == 2


def test_hatchling_build_includes_src_package() -> None:
    """A imagem instala o projeto a partir de src/, não de um pacote inexistente usiedu/."""
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.hatch.build.targets.wheel]" in pyproject
    assert 'packages = ["src"]' in pyproject


def test_frontend_proxy_preserves_upstream_host_for_container_apps() -> None:
    """O proxy usa o host interno da API para a descoberta de servico do ACA."""
    config = Path("frontend/nginx/default.conf.template").read_text(encoding="utf-8")

    assert "proxy_set_header Host $proxy_host;" in config
    assert "proxy_set_header Host $host;" not in config


def test_frontend_proxy_allows_api_cold_start() -> None:
    """Rotas comuns aguardam o bootstrap da API antes de retornar 504."""
    config = Path("frontend/nginx/default.conf.template").read_text(encoding="utf-8")

    assert "proxy_read_timeout 180s;" in config


def test_frontend_proxy_forwards_readiness_to_api() -> None:
    config = Path("frontend/nginx/default.conf.template").read_text(encoding="utf-8")

    readiness_block = config.split("location /ready", maxsplit=1)[1]
    assert "proxy_pass ${UPSTREAM_API_URL};" in readiness_block
    assert "proxy_set_header Host $proxy_host;" in readiness_block


def test_probe_workflow_is_manual_protected_and_preserves_api_template() -> None:
    workflow = Path(".github/workflows/configure-azure-api-probes.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "environment: production" in workflow
    assert "id-token: write" in workflow
    assert "az rest --method get" in workflow
    assert "az rest --method patch" in workflow
    assert ".properties.template" in workflow
    assert "Liveness" in workflow
    assert "Readiness" in workflow
    assert '"path": "/health"' in workflow
    assert '"path": "/ready"' in workflow
    assert "api-probes.json" in workflow
    assert "for attempt in $(seq 1 18)" in workflow
    assert "sleep 10" in workflow
    assert "${{ secrets." not in workflow.lower()


def test_api_image_declares_jwt_library_used_by_authentication() -> None:
    """A imagem deve instalar o pacote que fornece o modulo ``jwt``."""
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"PyJWT>=' in pyproject


def test_azure_deploy_declares_sqlite_on_azure_files() -> None:
    """O piloto em nuvem usa SQLite em Azure Files, eliminando custos de Postgres."""
    content = Path("infra/azure/main.bicep").read_text(encoding="utf-8")

    assert "resource postgresServer" not in content
    assert "name: 'USIEDU_DATABASE_URL'" not in content
    assert "name: 'USIEDU_FEEDBACK_DB'" in content
    assert "name: 'USIEDU_CACHE_DB'" in content
    assert "name: 'api-data'" in content

