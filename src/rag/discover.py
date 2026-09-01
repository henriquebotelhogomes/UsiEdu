"""Detecção de drift do menu lateral do Guia do Servidor (DGP/UnB).

Compara as URLs do menu lateral vivo com as entradas dgp.unb.br do manifest,
sem escrever nada. Útil para descobrir páginas novas/renomeadas no site que
ainda não foram curadas para a base de conhecimento.

Uso: python -m src.rag.discover

Exit codes: 0 = menu coberto pelo manifest; 1 = menu contém URL não indexada
ou a estrutura do site mudou (parser não encontrou seções).
"""

from __future__ import annotations

import logging
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from src.rag.ingest import load_manifest

logger = logging.getLogger(__name__)

SEED_URL = "https://dgp.unb.br/guia-do-servidor"
_FETCH_TIMEOUT = 60.0
# O site serve o guia em dois caminhos (alias); nenhum dos dois é "drift".
_GUIDE_PATHS = {"/guia-do-servidor", "/servidor/guia-servidor"}


class _SidebarParser(HTMLParser):
    """Extrai seções/links do padrão ``div.moduletable > h3.caixa_azul + ul.nav.menu``."""

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict[str, str]] = []
        self._in_module = False
        self._in_h3 = False
        self._in_menu = False
        self._in_anchor = False
        self._section = ""
        self._href = ""
        self._label: list[str] = []

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        for name, value in attrs:
            if name == "class" and value:
                return set(value.split())
        return set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = self._classes(attrs)
        if tag == "div":
            self._in_module = "moduletable" in classes
            self._section = ""
            self._in_menu = False
        elif tag == "h3" and self._in_module and "caixa_azul" in classes:
            self._in_h3 = True
        elif tag == "ul" and self._in_module and {"nav", "menu", "caixa_azul"} <= classes:
            self._in_menu = True
        elif tag == "a" and self._in_menu:
            self._in_anchor = True
            self._href = dict(attrs).get("href", "")
            self._label = []

    def handle_data(self, data: str) -> None:
        if self._in_h3:
            self._section += data.strip()
        elif self._in_anchor:
            self._label.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_anchor:
            self._in_anchor = False
            label = " ".join(part for part in self._label if part)
            if self._href and label:
                self.entries.append({"section": self._section, "label": label, "href": self._href})
        elif tag == "h3":
            self._in_h3 = False
        elif tag == "ul":
            self._in_menu = False


def parse_sidebar(html: str, base_url: str) -> list[dict[str, str]]:
    """Retorna ``[{section, label, href}]`` com hrefs absolutos (urljoin)."""
    parser = _SidebarParser()
    parser.feed(html)
    parser.close()
    for entry in parser.entries:
        entry["href"] = urljoin(base_url, entry["href"])
    return parser.entries


def _normalize_path(url: str) -> str:
    path = urlparse(url).path
    return path.rstrip("/") if len(path) > 1 else path


def classify(live: list[dict[str, str]], manifest_entries: list[dict]) -> dict:
    """Classifica o menu vivo contra o manifest (somente domínio do seed).

    - ``novas``: URLs internas do menu ausentes do manifest (drift acionável).
    - ``ok``: URLs internas do menu já cobertas pelo manifest.
    - ``removidas``: URLs dgp.unb.br do manifest fora do menu atual — informativo,
      inclui páginas profundas e curadoria manual; não gera exit 1.
    """
    base_netloc = urlparse(SEED_URL).netloc
    manifest_paths = {
        _normalize_path(doc["url"])
        for doc in manifest_entries
        if urlparse(doc["url"]).netloc == base_netloc
    }
    novas: list[dict[str, str]] = []
    ok: list[dict[str, str]] = []
    menu_paths: set[str] = set()
    for entry in live:
        parsed = urlparse(entry["href"])
        if parsed.netloc != base_netloc:
            continue
        path = _normalize_path(entry["href"])
        if path in _GUIDE_PATHS:
            continue
        menu_paths.add(path)
        (ok if path in manifest_paths else novas).append(entry)
    removidas = sorted(manifest_paths - menu_paths - _GUIDE_PATHS)
    return {"novas": novas, "ok": ok, "removidas": removidas}


def main() -> int:
    """Consulta o menu vivo, reporta classificação e retorna exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    try:
        resp = httpx.get(SEED_URL, timeout=_FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Falha ao consultar %s: %s", SEED_URL, exc)
        return 1

    live = parse_sidebar(resp.text, SEED_URL)
    if not live:
        logger.warning("Nenhuma seção do menu encontrada — o site pode ter mudado de estrutura.")
        return 1

    result = classify(live, load_manifest()["documents"])
    novas_paths = {_normalize_path(e["href"]) for e in result["novas"]}
    base_netloc = urlparse(SEED_URL).netloc

    for entry in live:
        parsed = urlparse(entry["href"])
        if parsed.netloc != base_netloc:
            logger.info("[externo] %s — %s", entry["label"], entry["href"])
            continue
        path = _normalize_path(entry["href"])
        if path in _GUIDE_PATHS:
            logger.info("[guia   ] %s", entry["label"])
            continue
        mark = "NOVO  " if path in novas_paths else "ok    "
        logger.info("[%s] %s — %s (%s)", mark, entry["section"], entry["label"], entry["href"])

    logger.info(
        "Resumo: %d ok, %d novas, %d no manifest fora do menu.",
        len(result["ok"]),
        len(result["novas"]),
        len(result["removidas"]),
    )
    for path in result["removidas"]:
        logger.info("  fora do menu atual: %s", path)

    if result["novas"]:
        logger.warning("Menu contém %d URL(s) não indexada(s) no manifest.", len(result["novas"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
