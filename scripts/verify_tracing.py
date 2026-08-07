"""Verificação do critério 6 — tracing LangSmith (RF-30).

Lista os runs recentes do projeto e confere se o trace contém o caminho
completo: supervisor -> agentes -> retriever -> LLM.

Uso: python scripts/verify_tracing.py
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Carrega o .env antes de criar o cliente
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

warnings.filterwarnings("ignore", category=DeprecationWarning)

from langsmith import Client  # noqa: E402

PROJECT = os.getenv("LANGSMITH_PROJECT", "usiedu-pilot")


def _as_text(value) -> str:
    """Converte inputs/outputs do run em texto pesquisável."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def main() -> None:
    client = Client()
    print(f"Projeto: {PROJECT}")

    runs = list(client.list_runs(project_name=PROJECT, limit=30))
    if not runs:
        print("Nenhum run encontrado no projeto.")
        return

    # Apenas runs reais da aplicação (descarta FakeChatModel de testes)
    runs = [r for r in runs if "FakeChatModel" not in (r.name or "")]

    print(f"\n{len(runs)} runs recentes da aplicação:")
    for r in runs:
        print(f"  - {r.start_time}  [{r.run_type}]  {r.name}  status={r.status}")

    nomes = " | ".join((r.name or "").lower() for r in runs)

    checks = {
        "grafo LangGraph": "langgraph" in nomes,
        "supervisor": "supervisor" in nomes,
        "roteamento": "route_from_supervisor" in nomes,
        "agente (academico/financeiro/documental)": any(
            a in nomes for a in ("academico", "financeiro", "documental")
        ),
        "LLM (ChatOpenAI)": "chatopenai" in nomes,
        "consolidação": "consolidation" in nomes,
    }

    # Evidência de RAG: o input do agente deve conter contexto recuperado
    evidencia_rag = ""
    for r in runs:
        if (r.name or "").lower() in ("academico", "financeiro", "documental"):
            blob = (_as_text(r.inputs) + _as_text(r.outputs)).lower()
            for marcador in ("calendário", "calendario", "feriado", "contexto", "documento"):
                if marcador in blob:
                    evidencia_rag = f"run '{r.name}' contém '{marcador}' no input/output"
                    break
        if evidencia_rag:
            break
    checks["retriever/RAG (contexto no agente)"] = bool(evidencia_rag)

    print("\nVerificação do caminho (critério 6):")
    for item, ok in checks.items():
        print(f"  {'[x]' if ok else '[ ]'} {item}")
    if evidencia_rag:
        print(f"      evidência: {evidencia_rag}")

    if all(checks.values()):
        print(
            "\nResultado: OK — trace contém o caminho completo "
            "supervisor -> agentes -> retriever -> LLM."
        )
    else:
        print("\nResultado: caminho incompleto — verifique os itens acima.")


if __name__ == "__main__":
    main()
