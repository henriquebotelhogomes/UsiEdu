"""Testes unitários do Agent Harness (runner, assertions, metrics, reporter)."""

from __future__ import annotations

import pytest

from src.harness.assertions import validate_scenario_result
from src.harness.metrics import calculate_harness_metrics
from src.harness.reporter import generate_markdown_report
from src.harness.runner import HarnessRunner
from src.harness.schema import (
    HarnessReport,
    HarnessScenario,
    TrajectoryResult,
)


@pytest.fixture
def sample_scenario() -> HarnessScenario:
    return HarnessScenario(
        id="SCEN-TEST-01",
        name="Teste de consulta acadêmica",
        category="academico",
        input_message="Qual minha nota de cálculo?",
        profile="student",
        expected_intent="academico",
        expected_nodes=["supervisor"],
        expected_tools=["get_notas"],
    )


class TestHarnessAssertions:
    """Testes dos validadores de asserções de loop."""

    def test_valida_cenario_com_sucesso(self, sample_scenario: HarnessScenario) -> None:
        result = TrajectoryResult(
            scenario_id=sample_scenario.id,
            scenario_name=sample_scenario.name,
            category=sample_scenario.category,
            passed=False,
            actual_intent="academico",
            visited_nodes=["supervisor", "academico"],
            executed_tools=["get_notas"],
            raw_answer="Sua nota é 8.5",
        )

        passed, assertions = validate_scenario_result(sample_scenario, result)
        assert passed is True
        assert len(assertions) >= 3

    def test_detecta_falha_de_intencao(self, sample_scenario: HarnessScenario) -> None:
        result = TrajectoryResult(
            scenario_id=sample_scenario.id,
            scenario_name=sample_scenario.name,
            category=sample_scenario.category,
            passed=False,
            actual_intent="financeiro",
            visited_nodes=["supervisor"],
            executed_tools=["get_notas"],
        )

        passed, assertions = validate_scenario_result(sample_scenario, result)
        assert passed is False
        intent_assert = next(a for a in assertions if a.assertion_name == "router_intent_match")
        assert intent_assert.passed is False


class TestHarnessMetrics:
    """Testes do cálculo de métricas agregadas."""

    def test_calcula_metricas_com_sucesso(self, sample_scenario: HarnessScenario) -> None:
        result = TrajectoryResult(
            scenario_id=sample_scenario.id,
            scenario_name=sample_scenario.name,
            category=sample_scenario.category,
            passed=True,
            actual_intent="academico",
            executed_tools=["get_notas"],
            duration_ms=120.5,
        )
        _, assertions = validate_scenario_result(sample_scenario, result)
        result.assertions = assertions

        metrics = calculate_harness_metrics([result])
        assert metrics.intent_accuracy == 1.0
        assert metrics.tool_precision == 1.0
        assert metrics.avg_latency_ms == 120.5


class TestHarnessRunner:
    """Testes do runner de cenários e suítes."""

    @pytest.mark.asyncio
    async def test_executa_cenario_em_modo_minimal(self, sample_scenario: HarnessScenario) -> None:
        runner = HarnessRunner(mode="minimal")
        result = await runner.run_scenario(sample_scenario)

        assert result.passed is True
        assert result.actual_intent == "academico"
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_executa_suite_completa_e_gera_relatorio(
        self, sample_scenario: HarnessScenario
    ) -> None:
        runner = HarnessRunner(mode="minimal")
        report: HarnessReport = await runner.run_suite([sample_scenario])

        assert report.total_scenarios == 1
        assert report.passed_scenarios == 1
        assert report.pass_rate == 1.0

        md = generate_markdown_report(report)
        assert "PASSOU" in md
        assert "Acurácia Intent" in md
