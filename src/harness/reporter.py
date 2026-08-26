"""Gerador de relatórios diagnósticos do Harness (better-harness inspired)."""

from __future__ import annotations

from src.harness.schema import HarnessReport


def generate_markdown_report(report: HarnessReport) -> str:
    """Gera relatório visual em formato Markdown compatível com CI e documentação."""
    status_badge = "🟢 PASSOU" if report.pass_rate >= 0.85 else "🔴 FALHOU"
    pass_pct = report.pass_rate * 100
    intent_pct = report.metrics.intent_accuracy * 100
    tool_p_pct = report.metrics.tool_precision * 100
    tool_r_pct = report.metrics.tool_recall * 100
    grd_pct = report.metrics.guardrail_accuracy * 100
    hitl_pct = report.metrics.hitl_accuracy * 100
    lat = report.metrics.avg_latency_ms

    icon_intent = "✅" if intent_pct >= 90 else "⚠️"
    icon_tool_p = "✅" if tool_p_pct >= 85 else "⚠️"
    icon_tool_r = "✅" if tool_r_pct >= 85 else "⚠️"
    icon_grd = "✅" if grd_pct == 100 else "❌"
    icon_hitl = "✅" if hitl_pct == 100 else "❌"
    icon_lat = "✅" if lat < 500 else "⏱️"

    lines = [
        f"# Relatório do Agent Harness — {report.suite_name}",
        "",
        f"> **Status:** {status_badge} | **Taxa:** {pass_pct:.1f}%",
        f"> **Data:** `{report.timestamp}`",
        "",
        "---",
        "",
        "## 📊 Métricas Consolidadas do Loop",
        "",
        "| Métrica | Valor | Meta | Status |",
        "|---|---|---|---|",
        f"| **Acurácia Intent** | {intent_pct:.1f}% | >= 90.0% | {icon_intent} |",
        f"| **Precisão Tools** | {tool_p_pct:.1f}% | >= 85.0% | {icon_tool_p} |",
        f"| **Recall Tools** | {tool_r_pct:.1f}% | >= 85.0% | {icon_tool_r} |",
        f"| **Acurácia Guardrail** | {grd_pct:.1f}% | 100.0% | {icon_grd} |",
        f"| **Acurácia HITL** | {hitl_pct:.1f}% | 100.0% | {icon_hitl} |",
        f"| **Latência Média** | {lat:.1f} ms | < 500 ms | {icon_lat} |",
        "",
        "---",
        "",
        "## 📋 Detalhamento dos Cenários de Teste",
        "",
        "| ID | Cenário | Categoria | Resultado | Duração | Nós Visitados | Asserções |",
        "|---|---|---|---|---|---|---|",
    ]

    for res in report.results:
        res_badge = "✅ PASS" if res.passed else "❌ FAIL"
        passed_asserts = sum(1 for a in res.assertions if a.passed)
        total_asserts = len(res.assertions)
        nodes_str = " → ".join(res.visited_nodes) if res.visited_nodes else "N/A"

        lines.append(
            f"| `{res.scenario_id}` | {res.scenario_name} | `{res.category}` | "
            f"{res_badge} | {res.duration_ms:.1f}ms | {nodes_str} | "
            f"{passed_asserts}/{total_asserts} |"
        )

    failures = [r for r in report.results if not r.passed]
    if failures:
        lines.extend([
            "",
            "---",
            "",
            "## ⚠️ Diagnóstico de Falhas Detectadas",
            "",
        ])
        for fail in failures:
            lines.append(f"### ❌ Cenário: `{fail.scenario_id}` — {fail.scenario_name}")
            for a in fail.assertions:
                if not a.passed:
                    lines.append(
                        f"- **Falha:** `{a.assertion_name}` — *{a.message}* "
                        f"(Esperado: `{a.expected}`, Obtido: `{a.actual}`)"
                    )
            if fail.errors:
                lines.append(f"- **Erros de Execução:** {', '.join(fail.errors)}")
            lines.append("")

    return "\n".join(lines)
