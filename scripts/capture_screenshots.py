"""Captura screenshots do UsiEdu para o README.

Pré-requisitos: frontend em http://localhost:5174 e API em http://localhost:8000.
Uso: python scripts/capture_screenshots.py
"""

import json
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5174"
API = "http://localhost:8000"
DOCS_URL = "https://henriquebotelhogomes.github.io/UsiEdu/"
OUT = Path(__file__).resolve().parent.parent / "screenshots"


def _post(url: str, payload: dict, token: str | None = None, timeout: int = 240) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def warm_up() -> None:
    """Aquece a API (login + 1ª chamada ao grafo) para evitar cold start nas capturas."""
    print("Aquecendo a API (1ª chamada ao LLM pode demorar)...")
    login = _post(f"{API}/auth/login", {"email": "ana@demo.usiedu", "password": "estudante123"})
    _post(f"{API}/chat", {"session_id": "sess-warmup", "message": "Olá"}, token=login["access_token"])
    print("API aquecida.")


def login_and_chat(page, nome_demo: str, pergunta: str) -> None:
    """Faz login pelo card demo e envia uma pergunta, aguardando a resposta."""
    page.goto(f"{BASE}/login")
    page.wait_for_load_state("networkidle")
    page.get_by_text(nome_demo).first.click()
    page.click('button[type="submit"]')
    page.wait_for_selector(".chat-page", timeout=90_000)
    page.fill('.input-area input[type="text"]', pergunta)
    page.click(".send-btn")
    page.wait_for_selector(".message.assistant", timeout=240_000)
    page.wait_for_selector(".loading", state="detached", timeout=240_000)
    page.wait_for_timeout(800)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    warm_up()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # 1. Landing page (página inteira)
        print("1/4 Landing page...")
        page.goto(f"{BASE}/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_500)
        page.screenshot(path=str(OUT / "landing-page.png"), full_page=True)

        # 2. Chat como estudante
        print("2/4 Chat estudante...")
        login_and_chat(page, "Ana Souza", "Quais feriados temos esse ano?")
        page.screenshot(path=str(OUT / "chat-estudante.png"), full_page=True)

        # 3. Chat como funcionário
        print("3/4 Chat funcionário...")
        page.click(".logout-btn")
        page.wait_for_timeout(500)
        login_and_chat(page, "Carlos Oliveira", "Como funciona a licença capacitação?")
        page.screenshot(path=str(OUT / "chat-funcionario.png"), full_page=True)

        # 4. Documentação MkDocs
        print("4/4 Documentação MkDocs...")
        page.goto(DOCS_URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1_000)
        page.screenshot(path=str(OUT / "docs-mkdocs.png"))

        browser.close()
    print(f"Screenshots salvos em {OUT}")


if __name__ == "__main__":
    main()
