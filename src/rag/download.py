"""Download dos documentos-fonte para knowledge_base/.

Uso: python -m src.rag.download
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = Path("knowledge_base")
MANIFEST_PATH = KNOWLEDGE_BASE_DIR / "manifest.json"

# Timeout generoso para PDFs grandes (regimento da UnB ~2MB)
_DOWNLOAD_TIMEOUT = 120.0


def compute_checksum(file_path: Path) -> str:
    """SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path) -> bool:
    """Baixa um arquivo da URL para o destino. Retorna True se sucesso."""
    if dest.exists():
        logger.info("  Arquivo já existe: %s", dest.name)
        return True

    logger.info("  Baixando %s...", url)
    try:
        with httpx.stream("GET", url, timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        logger.info("  Salvo: %s (%.1f KB)", dest.name, dest.stat().st_size / 1024)
        return True
    except Exception as exc:
        logger.error("  Falha no download de %s: %s", url, exc)
        return False


def main() -> None:
    """Baixa todos os documentos listados no manifest."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0

    for doc in manifest["documents"]:
        url = doc["url"]
        file_name = doc["file"]
        dest = KNOWLEDGE_BASE_DIR / file_name

        logger.info("Processando: %s", doc["name"])

        if download_file(url, dest):
            doc["checksum"] = compute_checksum(dest)
            success += 1
        else:
            failed += 1

    # Salva manifest com checksums
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Download completo: %d sucesso, %d falhas.", success, failed)
    if failed:
        logger.warning("Alguns documentos falharam. Verifique URLs e tente novamente.")


if __name__ == "__main__":
    main()
