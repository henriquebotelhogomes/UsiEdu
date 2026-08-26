"""Smoke autenticado sanitizado para o rollback público (T03.5)."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

DEMO_EMAIL = "ana@demo.usiedu"
DEMO_PASSWORD = "estudante123"
SMOKE_MESSAGE = "Qual e a finalidade do UsiEdu?"


def _request(method: str, url: str, payload: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=240) as response:
        return json.loads(response.read().decode("utf-8"))


def _route(method: str, path: str) -> dict[str, str]:
    return {"method": method, "path": path, "status": "ok"}


def run_smoke(base_url: str) -> dict:
    """Valida o fluxo demo sem escrever JWT, resposta ou identificadores na evidência."""
    base_url = base_url.rstrip("/")
    routes: list[dict[str, str]] = []

    health = _request("GET", f"{base_url}/health")
    if health.get("status") != "ok":
        raise RuntimeError("Health público não retornou status ok.")
    routes.append(_route("GET", "/health"))

    login = _request(
        "POST",
        f"{base_url}/auth/login",
        {"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    token = login["access_token"]
    routes.append(_route("POST", "/auth/login"))

    chat = _request(
        "POST",
        f"{base_url}/chat",
        {"session_id": f"rollback-smoke-{uuid.uuid4()}", "message": SMOKE_MESSAGE},
        token,
    )
    if not chat.get("answer"):
        raise RuntimeError("Chat público não retornou uma resposta.")
    routes.append(_route("POST", "/chat"))

    _request(
        "POST",
        f"{base_url}/feedback",
        {
            "session_id": chat["session_id"],
            "message_id": chat["message_id"],
            "rating": "up",
            "comment": "Smoke automatizado de rollback T03.5.",
        },
        token,
    )
    routes.append(_route("POST", "/feedback"))

    _request("GET", f"{base_url}/feedback/stats", token=token)
    routes.append(_route("GET", "/feedback/stats"))

    _request("GET", f"{base_url}/feedback/recent?limit=1", token=token)
    routes.append(_route("GET", "/feedback/recent?limit=1"))

    return {"schema_version": "1.0.0", "base_url": base_url, "routes": routes}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa smoke autenticado pós-rollback.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evidence = run_smoke(args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
