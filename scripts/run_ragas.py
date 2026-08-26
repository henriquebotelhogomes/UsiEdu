"""Helper script para execução de avaliação Ragas e CI Quality Gate (RF4-04).

Uso:
    python scripts/run_ragas.py --ci-gate --min-score 0.80
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona a raiz ao sys.path
raiz = Path(__file__).resolve().parent.parent
if str(raiz) not in sys.path:
    sys.path.insert(0, str(raiz))

from src.evaluation.run_ragas import main

if __name__ == "__main__":
    main()
