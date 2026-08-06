"""Download da LDB com timeout maior e user-agent de navegador."""

import os
from pathlib import Path

import httpx

URL = "https://www.planalto.gov.br/ccivil_03/leis/l9394.htm"
DEST = Path("knowledge_base") / "ldb_9394_96.html"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}

try:
    with httpx.stream("GET", URL, timeout=300.0, follow_redirects=True, headers=HEADERS) as resp:
        resp.raise_for_status()
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', '')}")
        with open(DEST, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    size = os.path.getsize(DEST)
    print(f"Salvo: {size / 1024:.1f} KB")
except Exception as exc:
    print(f"FALHA: {type(exc).__name__}: {str(exc)[:200]}")
