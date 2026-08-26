#!/usr/bin/env python
"""CLI do Agent Harness do UsiEdu (better-harness & deepseek-harness inspired).

Executa a suíte de avaliação de trajetórias, ferramentas, guardrails e HITL.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.harness.reporter import generate_markdown_report
from src.harness.runner import HarnessRunner


async def _run(args: argparse.Namespace) -> int:
    runner = HarnessRunner(mode=args.mode)
    scenarios_dir = PROJECT_ROOT / "src" / "harness" / "scenarios"

    if args.suite != "all":
        target_file = scenarios_dir / f"{args.suite}.json"
        if not target_file.exists():
            print(f"[ERROR] Suite '{args.suite}' nao encontrada em {scenarios_dir}")
            return 1
        scenarios = runner.load_scenarios_from_directory(scenarios_dir)
        scenarios = [s for s in scenarios if s.category == args.suite]
    else:
        scenarios = runner.load_scenarios_from_directory(scenarios_dir)

    if not scenarios:
        print("[WARN] Nenhum cenario encontrado para execucao.")
        return 0

    print(f"=== INICIANDO AGENT HARNESS ({len(scenarios)} cenários, Modo: {args.mode}) ===")
    report = await runner.run_suite(scenarios, suite_name=f"UsiEdu Suite ({args.suite})")

    # Gera relatório Markdown
    markdown_output = generate_markdown_report(report)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown_output, encoding="utf-8")
        print(f"[INFO] Relatorio salvo em: {out_path}")

    # Exibe resumo no console
    print("\n--- RESUMO DE EXECUCAO DO HARNESS ---")
    print(f"Total de Cenarios : {report.total_scenarios}")
    print(f"Aprovados         : {report.passed_scenarios}")
    print(f"Reprovados        : {report.failed_scenarios}")
    print(f"Taxa de Sucesso   : {report.pass_rate * 100:.1f}%")
    print(f"Acuracia Intent   : {report.metrics.intent_accuracy * 100:.1f}%")
    print(f"Precisao Tools    : {report.metrics.tool_precision * 100:.1f}%")
    print(f"Acuracia Guardrail: {report.metrics.guardrail_accuracy * 100:.1f}%")
    print(f"Latencia Media    : {report.metrics.avg_latency_ms:.1f}ms")

    if args.ci_gate:
        rate_pct = args.min_pass_rate * 100
        print(f"\n[CI-GATE] Validando taxa minima de aprovacao de {rate_pct:.1f}%...")
        if report.pass_rate < args.min_pass_rate:
            print(f"[CI-GATE] [FAIL] Taxa de {report.pass_rate * 100:.1f}% abaixo do threshold!")
            return 1
        print("[CI-GATE] [OK] Quality Gate aprovado com sucesso!")

    return 0 if report.failed_scenarios == 0 or not args.ci_gate else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Executor do Agent Harness da UsiEdu")
    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "academico", "financeiro", "hitl", "guardrail"],
        help="Suíte ou categoria funcional a ser executada",
    )
    parser.add_argument(
        "--mode",
        default="minimal",
        choices=["minimal", "standard"],
        help="Modo de execução (minimal: mock determinístico sem custo; standard: LLM ativo)",
    )
    parser.add_argument(
        "--ci-gate",
        action="store_true",
        help="Bloqueia CI com exit code 1 se a taxa de aprovação ficar abaixo do threshold",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.90,
        help="Taxa mínima de aprovação exigida para o CI Gate (padrão: 0.90)",
    )
    parser.add_argument(
        "--output",
        default="src/harness/relatorio_harness.md",
        help="Caminho do arquivo Markdown de saída para o relatório",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(_run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
