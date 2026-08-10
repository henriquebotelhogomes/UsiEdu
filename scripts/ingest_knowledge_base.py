"""Executa a ingestão da base de conhecimento no ambiente configurado.

Uso: python scripts/ingest_knowledge_base.py
"""

from __future__ import annotations

import sys

from src.rag.ingest import main

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
