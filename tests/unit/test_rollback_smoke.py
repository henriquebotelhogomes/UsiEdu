"""Testes do smoke autenticado sanitizado do rollback (T03.5)."""

from __future__ import annotations

from src.delivery import rollback_smoke


def test_run_smoke_exercises_demo_login_chat_feedback_and_insights(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    responses = iter(
        [
            {"status": "ok"},
            {"access_token": "jwt-should-not-be-reported"},
            {
                "session_id": "rollback-smoke-session",
                "message_id": "rollback-smoke-message",
                "answer": "Resposta demo.",
            },
            {"status": "ok", "feedback_id": 1},
            {"total": 1, "up": 1, "down": 0, "satisfaction": 1.0},
            {"items": []},
        ]
    )

    def fake_request(
        method: str, url: str, payload: dict | None = None, token: str | None = None
    ) -> dict:
        calls.append((method, url))
        return next(responses)

    monkeypatch.setattr(rollback_smoke, "_request", fake_request)

    evidence = rollback_smoke.run_smoke("https://usiedu.example.com")

    assert [method for method, _ in calls] == ["GET", "POST", "POST", "POST", "GET", "GET"]
    assert [url.rsplit("/", maxsplit=1)[-1] for _, url in calls] == [
        "health",
        "login",
        "chat",
        "feedback",
        "stats",
        "recent?limit=1",
    ]
    assert evidence == {
        "schema_version": "1.0.0",
        "base_url": "https://usiedu.example.com",
        "routes": [
            {"method": "GET", "path": "/health", "status": "ok"},
            {"method": "POST", "path": "/auth/login", "status": "ok"},
            {"method": "POST", "path": "/chat", "status": "ok"},
            {"method": "POST", "path": "/feedback", "status": "ok"},
            {"method": "GET", "path": "/feedback/stats", "status": "ok"},
            {"method": "GET", "path": "/feedback/recent?limit=1", "status": "ok"},
        ],
    }
