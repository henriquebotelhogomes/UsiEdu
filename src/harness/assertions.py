"""Validadores e asserções de loop para trajetórias de agentes (better-harness inspired)."""

from __future__ import annotations

from src.harness.schema import AssertionResult, HarnessScenario, TrajectoryResult


def validate_scenario_result(
    scenario: HarnessScenario,
    result: TrajectoryResult,
) -> tuple[bool, list[AssertionResult]]:
    """Valida todas as expectativas de um cenário contra o resultado obtido."""
    assertions: list[AssertionResult] = []

    # 1. Validação de Intenção do Roteador
    if scenario.expected_intent:
        passed = result.actual_intent == scenario.expected_intent
        msg = f"Intent esperado '{scenario.expected_intent}', obtido '{result.actual_intent}'"
        assertions.append(
            AssertionResult(
                assertion_name="router_intent_match",
                passed=passed,
                expected=scenario.expected_intent,
                actual=result.actual_intent,
                message=msg,
            )
        )

    # 2. Validação de Nós Visitados na Trajetória
    for expected_node in scenario.expected_nodes:
        passed = expected_node in result.visited_nodes
        assertions.append(
            AssertionResult(
                assertion_name=f"visited_node_{expected_node}",
                passed=passed,
                expected=expected_node,
                actual=result.visited_nodes,
                message=f"Nó obrigatório '{expected_node}' visitado na trajetória",
            )
        )

    # 3. Validação de Chamadas de Ferramentas (@tool)
    for expected_tool in scenario.expected_tools:
        passed = expected_tool in result.executed_tools
        assertions.append(
            AssertionResult(
                assertion_name=f"tool_executed_{expected_tool}",
                passed=passed,
                expected=expected_tool,
                actual=result.executed_tools,
                message=f"Ferramenta '{expected_tool}' executada pelo especialista",
            )
        )

    # 4. Validação de Ferramentas Proibidas
    for forbidden_tool in scenario.forbidden_tools:
        passed = forbidden_tool not in result.executed_tools
        assertions.append(
            AssertionResult(
                assertion_name=f"tool_forbidden_{forbidden_tool}",
                passed=passed,
                expected=f"NOT_{forbidden_tool}",
                actual=result.executed_tools,
                message=f"Ferramenta proibida '{forbidden_tool}' não foi invocada",
            )
        )

    # 5. Validação de Guardrail & Sanitização de PII
    if scenario.expect_pii_masking:
        assertions.append(
            AssertionResult(
                assertion_name="pii_masked_successfully",
                passed=result.pii_masked,
                expected=True,
                actual=result.pii_masked,
                message="Dados sensíveis (PII) foram detectados e mascarados",
            )
        )

    if scenario.expect_guardrail_trigger:
        assertions.append(
            AssertionResult(
                assertion_name="guardrail_triggered",
                passed=result.guardrail_triggered,
                expected=True,
                actual=result.guardrail_triggered,
                message="Tentativa maliciosa ou prompt injection foi bloqueada por guardrail",
            )
        )

    # 6. Validação de Human-in-the-Loop Interrupt
    if scenario.expect_hitl_interrupt:
        assertions.append(
            AssertionResult(
                assertion_name="hitl_interrupt_paused",
                passed=result.hitl_interrupted,
                expected=True,
                actual=result.hitl_interrupted,
                message="Fluxo pausou corretamente antes do nó crítico para aprovação humana",
            )
        )

    # 7. Validação de Ciclos Máximos no Grafo
    cycle_passed = result.cycle_count <= scenario.max_cycles
    cycle_msg = f"Ciclos ({result.cycle_count}) dentro do limite ({scenario.max_cycles})"
    assertions.append(
        AssertionResult(
            assertion_name="cycle_budget_respected",
            passed=cycle_passed,
            expected=f"<= {scenario.max_cycles}",
            actual=result.cycle_count,
            message=cycle_msg,
        )
    )

    # 8. Validação de Conteúdo da Resposta Final
    for snippet in scenario.expected_answer_contains:
        passed = snippet.lower() in result.raw_answer.lower()
        assertions.append(
            AssertionResult(
                assertion_name=f"answer_contains_{snippet[:20]}",
                passed=passed,
                expected=snippet,
                actual=result.raw_answer[:100],
                message=f"Resposta contém trecho esperado: '{snippet}'",
            )
        )

    all_passed = all(a.passed for a in assertions)
    return all_passed, assertions
