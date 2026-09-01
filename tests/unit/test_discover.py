"""Testes do detector de drift do menu lateral (src/rag/discover)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag import discover, ingest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "sidebar_sample.html"

EXPECTED_SECTIONS = [
    "Servidor",
    "SIGRH",
    "Carreira - Avaliações e Progressões",
    "Capacitação",
    "Saúde",
]


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


@pytest.fixture()
def sidebar_html() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


@pytest.fixture()
def manifest_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": []}), encoding="utf-8")
    monkeypatch.setattr(ingest, "MANIFEST_PATH", manifest)
    return manifest


def test_parse_sidebar_extrai_cinco_secoes_e_24_links(sidebar_html: str) -> None:
    entries = discover.parse_sidebar(sidebar_html, discover.SEED_URL)

    assert list(dict.fromkeys(e["section"] for e in entries)) == EXPECTED_SECTIONS
    assert len(entries) == 24


def test_parse_sidebar_resolve_hrefs_e_preserva_externo(sidebar_html: str) -> None:
    entries = discover.parse_sidebar(sidebar_html, discover.SEED_URL)

    externo = [e for e in entries if "capacitacao.unb.br" in e["href"]]
    assert externo and externo[0]["label"] == "Cursos e eventos"

    afastamentos = [e for e in entries if e["href"] == "https://dgp.unb.br/afastamentos"]
    assert afastamentos and afastamentos[0]["label"] == "Licença e Afastamentos"
    assert afastamentos[0]["section"] == "Capacitação"


def test_classify_detecta_novas_e_ok(sidebar_html: str) -> None:
    live = discover.parse_sidebar(sidebar_html, discover.SEED_URL)
    manifest_entries = [
        {"name": "Licença e Afastamentos", "url": "https://dgp.unb.br/afastamentos"},
        {"name": "SIGRH — Sobre", "url": "https://dgp.unb.br/sigrh-sobre"},
    ]

    result = discover.classify(live, manifest_entries)

    assert {e["href"] for e in result["ok"]} == {
        "https://dgp.unb.br/afastamentos",
        "https://dgp.unb.br/sigrh-sobre",
    }
    novas_paths = {discover._normalize_path(e["href"]) for e in result["novas"]}
    assert "/sougovbr" in novas_paths
    # 24 links - guia - externo - 2 cobertos
    assert len(result["novas"]) == 20


def test_classify_ignora_alias_do_guia_e_dominio_externo(sidebar_html: str) -> None:
    live = discover.parse_sidebar(sidebar_html, discover.SEED_URL)

    result = discover.classify(
        live, [{"name": "Guia", "url": "https://dgp.unb.br/servidor/guia-servidor"}]
    )

    hrefs = {e["href"] for e in result["novas"] + result["ok"]}
    assert not any("capacitacao.unb.br" in href for href in hrefs)
    assert not any(href.endswith("guia-do-servidor") for href in hrefs)
    assert result["removidas"] == []


def test_classify_relata_paginas_do_manifest_fora_do_menu(sidebar_html: str) -> None:
    live = discover.parse_sidebar(sidebar_html, discover.SEED_URL)

    result = discover.classify(
        live, [{"name": "Legislacao", "url": "https://dgp.unb.br/legislacao-federal"}]
    )

    assert result["removidas"] == ["/legislacao-federal"]


def test_main_exit_1_quando_menu_tem_url_nova(
    sidebar_html: str,
    manifest_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(discover.httpx, "get", lambda *args, **kwargs: _FakeResponse(sidebar_html))

    assert discover.main() == 1


def test_main_exit_0_quando_menu_coberto(
    sidebar_html: str,
    manifest_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = discover.parse_sidebar(sidebar_html, discover.SEED_URL)
    manifest_path.write_text(
        json.dumps({"documents": [{"name": e["label"], "url": e["href"]} for e in live]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(discover.httpx, "get", lambda *args, **kwargs: _FakeResponse(sidebar_html))

    assert discover.main() == 0
