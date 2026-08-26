"""Métricas de qualidade, acurácia e eficiência do Harness (deepseek-harness inspired)."""

from __future__ import annotations

from src.harness.schema import HarnessMetrics, TrajectoryResult


def calculate_harness_metrics(results: list[TrajectoryResult]) -> HarnessMetrics:
    """Calcula métricas agregadas a partir dos resultados dos cenários."""
    if not results:
        return HarnessMetrics()

    intent_matches = 0
    intent_total = 0

    tools_expected_count = 0
    tools_matched_count = 0
    tools_executed_count = 0

    guardrails_expected = 0
    guardrails_passed = 0

    hitl_expected = 0
    hitl_passed = 0

    total_latency = 0.0

    for res in results:
        total_latency += res.duration_ms

        for assertion in res.assertions:
            if assertion.assertion_name == "router_intent_match":
                intent_total += 1
                if assertion.passed:
                    intent_matches += 1

            elif assertion.assertion_name.startswith("tool_executed_"):
                tools_expected_count += 1
                if assertion.passed:
                    tools_matched_count += 1

            elif assertion.assertion_name in ("pii_masked_successfully", "guardrail_triggered"):
                guardrails_expected += 1
                if assertion.passed:
                    guardrails_passed += 1

            elif assertion.assertion_name == "hitl_interrupt_paused":
                hitl_expected += 1
                if assertion.passed:
                    hitl_passed += 1

        tools_executed_count += len(res.executed_tools)

    intent_acc = (intent_matches / intent_total) if intent_total > 0 else 1.0
    tool_prec = (tools_matched_count / tools_executed_count) if tools_executed_count > 0 else 1.0
    tool_rec = (tools_matched_count / tools_expected_count) if tools_expected_count > 0 else 1.0
    guardrail_acc = (guardrails_passed / guardrails_expected) if guardrails_expected > 0 else 1.0
    hitl_acc = (hitl_passed / hitl_expected) if hitl_expected > 0 else 1.0
    avg_lat = total_latency / len(results)

    return HarnessMetrics(
        intent_accuracy=round(intent_acc, 4),
        tool_precision=round(tool_prec, 4),
        tool_recall=round(tool_rec, 4),
        guardrail_accuracy=round(guardrail_acc, 4),
        hitl_accuracy=round(hitl_acc, 4),
        avg_latency_ms=round(avg_lat, 2),
    )
