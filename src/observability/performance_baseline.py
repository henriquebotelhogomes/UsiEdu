"""Coleta sanitizada de baseline cold/warm para o protocolo T05.1."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from src.observability.performance_protocol import validate_and_split_samples

MEASUREMENT_MESSAGE = "Quero ver minhas notas."
DEPENDENCY_OUTCOMES = {
    "llm": "not_measured",
    "qdrant": "not_measured",
    "postgresql": "not_measured",
}
MODELS = {
    "router": "not_reported",
    "agent": "not_reported",
    "embedder": "not_reported",
    "reranker": "not_reported",
}


def classify_temperature(initial_replica_count: int) -> str:
    """Classifica cold somente quando Azure não reportou réplicas antes do teste."""
    return "cold" if initial_replica_count == 0 else "warm"


def sanitize_status(*, status_code: int, error: Exception | None = None) -> dict[str, int | str]:
    """Retorna status agregado sem serializar detalhe de erro ou resposta."""
    if error is not None:
        return {"status_code": status_code, "outcome": "transport_error"}
    if 200 <= status_code < 300:
        return {"status_code": status_code, "outcome": "ok"}
    return {"status_code": status_code, "outcome": "http_error"}


def require_uncached_final_event(event: dict[str, Any]) -> None:
    """Recusa respostas servidas do cache para preservar a medição do fluxo real."""
    if event.get("event") == "final" and event.get("from_cache") is True:
        raise ValueError("chat measurement must not use cache")


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sample(
    *,
    sample_id: str,
    temperature: str,
    scenario: str,
    started_at: str,
    completed_at: str,
    revision: str,
    replica_count: int,
    status: dict[str, int | str],
    latency_ms: dict[str, float],
) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "temperature": temperature,
        "scenario": scenario,
        "started_at": started_at,
        "completed_at": completed_at,
        "revision": revision,
        "replica_count": replica_count,
        "models": MODELS,
        "status_code": status["status_code"],
        "latency_ms": latency_ms,
        "dependency_outcomes": DEPENDENCY_OUTCOMES,
        "exit_137_observed": False,
    }


async def _measure_health(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    temperature: str,
    revision: str,
    replica_count: int,
) -> dict[str, Any]:
    started_at = _timestamp()
    started = time.perf_counter()
    try:
        response = await client.get(f"{base_url}/health")
        status = sanitize_status(status_code=response.status_code)
    except httpx.HTTPError as exc:
        status = sanitize_status(status_code=0, error=exc)
    completed_at = _timestamp()
    return _sample(
        sample_id=f"{temperature}-health-001",
        temperature=temperature,
        scenario="health",
        started_at=started_at,
        completed_at=completed_at,
        revision=revision,
        replica_count=replica_count,
        status=status,
        latency_ms={"total": round((time.perf_counter() - started) * 1000, 3)},
    )


async def _login(
    client: httpx.AsyncClient, *, base_url: str, email: str, password: str
) -> tuple[dict[str, Any], str]:
    started_at = _timestamp()
    started = time.perf_counter()
    try:
        response = await client.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password},
        )
        status = sanitize_status(status_code=response.status_code)
        token = response.json().get("access_token", "") if status["outcome"] == "ok" else ""
    except (httpx.HTTPError, ValueError) as exc:
        status = sanitize_status(status_code=0, error=exc)
        token = ""
    completed_at = _timestamp()
    sample = _sample(
        sample_id="warm-login-001",
        temperature="warm",
        scenario="login",
        started_at=started_at,
        completed_at=completed_at,
        revision="not_reported",
        replica_count=0,
        status=status,
        latency_ms={"total": round((time.perf_counter() - started) * 1000, 3)},
    )
    if not token:
        raise RuntimeError("demo login did not return an access token")
    return sample, token


async def _measure_chat(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    token: str,
    sample_number: int,
    revision: str,
    replica_count: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        started_at = _timestamp()
        started = time.perf_counter()
        first_token_at: float | None = None
        status_code = 0
        try:
            async with client.stream(
                "POST",
                f"{base_url}/chat/stream",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "session_id": f"performance-{uuid.uuid4()}",
                    "message": MEASUREMENT_MESSAGE,
                },
            ) as response:
                status_code = response.status_code
                if 200 <= status_code < 300:
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        event = json.loads(line.removeprefix("data: "))
                        if event.get("event") == "token" and first_token_at is None:
                            first_token_at = time.perf_counter()
                        require_uncached_final_event(event)
                status = sanitize_status(status_code=status_code)
        except (httpx.HTTPError, ValueError) as exc:
            status = sanitize_status(status_code=status_code, error=exc)

        if status["outcome"] != "ok" or first_token_at is None:
            raise RuntimeError("chat measurement did not receive a successful first token")

        completed_at = _timestamp()
        return _sample(
            sample_id=f"warm-chat-{sample_number:03d}",
            temperature="warm",
            scenario="chat",
            started_at=started_at,
            completed_at=completed_at,
            revision=revision,
            replica_count=replica_count,
            status=status,
            latency_ms={
                "first_token": round((first_token_at - started) * 1000, 3),
                "total": round((time.perf_counter() - started) * 1000, 3),
            },
        )


async def collect_baseline(
    *,
    base_url: str,
    email: str,
    password: str,
    revision: str,
    initial_replica_count: int,
    concurrent_users: int,
    burst_requests: int,
) -> dict[str, Any]:
    """Coleta uma baseline sanitizada sem reter credencial, token ou conteúdo."""
    if concurrent_users != 5 or burst_requests != 10:
        raise ValueError("baseline must use five concurrent users and a burst of ten")
    if initial_replica_count != 0:
        raise ValueError("baseline requires zero replicas before the cold health sample")

    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        cold_health = await _measure_health(
            client,
            base_url=base_url.rstrip("/"),
            temperature=classify_temperature(initial_replica_count),
            revision=revision,
            replica_count=initial_replica_count,
        )
        login, token = await _login(
            client, base_url=base_url.rstrip("/"), email=email, password=password
        )
        login["revision"] = revision
        login["replica_count"] = initial_replica_count

        semaphore = asyncio.Semaphore(concurrent_users)
        chat_samples = await asyncio.gather(
            *(
                _measure_chat(
                    client,
                    base_url=base_url.rstrip("/"),
                    token=token,
                    sample_number=number,
                    revision=revision,
                    replica_count=initial_replica_count,
                    semaphore=semaphore,
                )
                for number in range(1, burst_requests + 1)
            )
        )

    report = {
        "schema_version": "1.0.0",
        "evidence_kind": "performance_measurement",
        "environment": "azure",
        "load_profile": {"concurrent_users": concurrent_users, "burst_requests": burst_requests},
        "samples": [cold_health, login, *chat_samples],
    }
    validate_and_split_samples(report)
    return report


def main() -> None:
    """Executa a baseline protegida e grava somente o relatório sanitizado."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--initial-replica-count", type=int, required=True)
    parser.add_argument("--concurrent-users", type=int, required=True)
    parser.add_argument("--burst-requests", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = asyncio.run(
        collect_baseline(
            base_url=args.base_url,
            email=args.email,
            password=args.password,
            revision=args.revision,
            initial_replica_count=args.initial_replica_count,
            concurrent_users=args.concurrent_users,
            burst_requests=args.burst_requests,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
