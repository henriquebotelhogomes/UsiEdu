"""Módulo de Harness de Agentes do UsiEdu.

Inspirado em QoderAI/better-harness e DeepSeek AI/deepseek-harness:
- Avaliação determinística de trajetórias multi-agente
- Verificação de chamadas de ferramentas (@tool)
- Validação de guardrails, PII e Human-in-the-Loop
- Métricas de eficiência de loop e Quality Gate
"""

from __future__ import annotations

from src.harness.assertions import validate_scenario_result
from src.harness.metrics import calculate_harness_metrics
from src.harness.reporter import generate_markdown_report
from src.harness.runner import HarnessRunner
from src.harness.schema import (
    HarnessReport,
    HarnessScenario,
    StepTelemetry,
    TrajectoryResult,
)

__all__ = [
    "HarnessReport",
    "HarnessRunner",
    "HarnessScenario",
    "StepTelemetry",
    "TrajectoryResult",
    "calculate_harness_metrics",
    "generate_markdown_report",
    "validate_scenario_result",
]
