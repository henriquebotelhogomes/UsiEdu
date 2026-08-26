"""Schemas e modelos Pydantic para o Harness de Agentes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HarnessScenario(BaseModel):
    """Definição declarativa de um cenário de teste do agente (Harness-as-Code)."""

    id: str = Field(..., description="Identificador único do cenário (ex: SCEN-ACAD-01)")
    name: str = Field(..., description="Nome descritivo do cenário")
    description: str = Field(default="", description="Contexto e objetivo do teste")
    category: Literal[
        "academico",
        "financeiro",
        "institucional",
        "composto",
        "hitl",
        "guardrail",
    ] = Field(..., description="Categoria funcional do cenário")

    # Inputs de Execução
    input_message: str = Field(..., description="Mensagem de entrada do usuário")
    profile: Literal["student", "staff"] = Field(default="student", description="Perfil do usuário")
    user_id: str = Field(default="ana@demo.usiedu", description="E-mail ou ID do usuário")
    session_id: str | None = Field(default=None, description="Session ID opcional")

    # Expectativas e Asserções (Assertions)
    expected_intent: str | None = Field(
        default=None,
        description="Intenção esperada (academico, financeiro, institucional, composta, etc.)",
    )
    expected_nodes: list[str] = Field(
        default_factory=list,
        description="Nós do grafo que devem ser visitados na trajetória",
    )
    expected_tools: list[str] = Field(
        default_factory=list,
        description="Ferramentas (@tool) que devem ser executadas pelo agente",
    )
    forbidden_tools: list[str] = Field(
        default_factory=list,
        description="Ferramentas que NÃO devem ser acionadas",
    )
    expect_pii_masking: bool = Field(
        default=False,
        description="Se o input continha PII que deveria ser ofuscado",
    )
    expect_guardrail_trigger: bool = Field(
        default=False,
        description="Se o guardrail de injeção ou saída deveria ser disparado",
    )
    expect_hitl_interrupt: bool = Field(
        default=False,
        description="Se o grafo deve pausar em interrupt_before para aprovação humana",
    )
    max_cycles: int = Field(
        default=2,
        description="Limite máximo de ciclos permitidos no grafo para este cenário",
    )
    expected_answer_contains: list[str] = Field(
        default_factory=list,
        description="Trechos obrigatórios que devem estar presentes na resposta final",
    )


class StepTelemetry(BaseModel):
    """Telemetria de um passo individual da execução do agente."""

    step_index: int
    node_name: str
    tool_calls: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


class AssertionResult(BaseModel):
    """Resultado de uma validação individual de asserção."""

    assertion_name: str
    passed: bool
    expected: Any
    actual: Any
    message: str = ""


class TrajectoryResult(BaseModel):
    """Resultado da execução e validação completa de um cenário."""

    scenario_id: str
    scenario_name: str
    category: str
    passed: bool
    duration_ms: float = 0.0

    actual_intent: str | None = None
    visited_nodes: list[str] = Field(default_factory=list)
    executed_tools: list[str] = Field(default_factory=list)
    raw_answer: str = ""
    pii_masked: bool = False
    guardrail_triggered: bool = False
    hitl_interrupted: bool = False
    cycle_count: int = 0

    assertions: list[AssertionResult] = Field(default_factory=list)
    telemetry: list[StepTelemetry] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class HarnessMetrics(BaseModel):
    """Métricas consolidadas de qualidade e performance do harness."""

    intent_accuracy: float = 1.0
    tool_precision: float = 1.0
    tool_recall: float = 1.0
    guardrail_accuracy: float = 1.0
    hitl_accuracy: float = 1.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0


class HarnessReport(BaseModel):
    """Relatório completo consolidado de uma rodada de harness."""

    suite_name: str = "UsiEdu Agent Suite"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    total_scenarios: int = 0
    passed_scenarios: int = 0
    failed_scenarios: int = 0
    pass_rate: float = 0.0
    metrics: HarnessMetrics = Field(default_factory=HarnessMetrics)
    results: list[TrajectoryResult] = Field(default_factory=list)
