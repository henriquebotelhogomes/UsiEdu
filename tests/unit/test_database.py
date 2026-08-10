"""Contrato de seleção do armazenamento persistente."""

from __future__ import annotations


def test_database_url_prefere_postgres_configurado(monkeypatch) -> None:
    monkeypatch.setenv("USIEDU_DATABASE_URL", "postgresql://usiedu:senha@db:5432/usiedu")

    from src.storage.database import database_url

    assert database_url() == "postgresql://usiedu:senha@db:5432/usiedu"


def test_database_url_ausente_mantem_compatibilidade_local(monkeypatch) -> None:
    monkeypatch.delenv("USIEDU_DATABASE_URL", raising=False)

    from src.storage.database import database_url

    assert database_url() is None
