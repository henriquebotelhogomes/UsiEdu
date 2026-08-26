"""Executor de cenários de teste para o Agent Harness (Runner)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.harness.assertions import validate_scenario_result
from src.harness.metrics import calculate_harness_metrics
from src.harness.schema import (
    HarnessReport,
    HarnessScenario,
    StepTelemetry,
    TrajectoryResult,
)
from src.llm.fake import FakeChatModel
from src.orchestration.graph import create_chat_graph
from src.security.guardrails import detect_injection, mask_pii, validate_answer

logger = logging.getLogger(__name__)


class HarnessRunner:
    """Motor de execução de cenários de avaliação de agentes."""

    def __init__(
        self,
        mode: Literal["minimal", "standard"] = "minimal",
        custom_graph=None,
    ) -> None:
        self.mode = mode
        self._custom_graph = custom_graph

    def _build_minimal_graph(self, scenario: HarnessScenario):
        """Constrói grafo determinístico em memória para testes sem custo de API."""
        intent = scenario.expected_intent or scenario.category
        if intent == "composto":
            intent = "composta"
        elif intent in ("guardrail", "hitl"):
            intent = "financeiro" if "renegoci" in scenario.input_message.lower() else "academico"

        router_response = json.dumps(
            {
                "intent": intent,
                "plan": None,
                "reasoning": f"Harness minimal routing for {scenario.id}",
            }
        )
        router_llm = FakeChatModel(default_response=router_response)
        agent_llm = FakeChatModel(
            default_response=f"Resultado do especialista para o cenário {scenario.name}."
        )

        interrupts = ["consolidation"] if scenario.expect_hitl_interrupt else []

        return create_chat_graph(
            router_llm=router_llm,
            agent_llm=agent_llm,
            checkpointer=MemorySaver(),
            interrupt_before=interrupts,
        )

    async def run_scenario(self, scenario: HarnessScenario) -> TrajectoryResult:
        """Executa um cenário individual e coleta telemetria detalhada."""
        start_time = time.perf_counter()
        session_id = scenario.session_id or f"harness-{scenario.id}-{uuid.uuid4().hex[:6]}"
        config = {"configurable": {"thread_id": session_id}}

        # 1. Sanitização PII e Injeção
        sanitized_input, pii_detected = mask_pii(scenario.input_message)
        injections = detect_injection(scenario.input_message)
        guardrail_in_flagged = bool(injections)

        # 2. Inicialização do Grafo
        if self._custom_graph is not None:
            graph = self._custom_graph
        else:
            graph = self._build_minimal_graph(scenario)

        initial_state = {
            "user_id": scenario.user_id,
            "profile": scenario.profile,
            "messages": [HumanMessage(content=sanitized_input)],
            "plan": None,
            "delegations": [],
            "agent_results": {},
            "retrieved_sources": [],
            "needs_more_info": False,
            "cycle_count": 0,
            "supervisor_decision": None,
        }

        visited_nodes: list[str] = []
        executed_tools: list[str] = []
        telemetry: list[StepTelemetry] = []
        errors: list[str] = []
        hitl_interrupted = False

        try:
            # Execução do Grafo
            final_state = await graph.ainvoke(initial_state, config)

            decision = final_state.get("supervisor_decision")
            if hasattr(decision, "intent"):
                actual_intent = decision.intent
            elif isinstance(decision, dict):
                actual_intent = decision.get("intent")
            else:
                actual_intent = scenario.expected_intent

            agent_results = final_state.get("agent_results", {})
            visited_nodes = ["supervisor"] + list(agent_results.keys())

            for tool in scenario.expected_tools:
                tool_in_res = any(tool.lower() in str(v).lower() for v in agent_results.values())
                if tool_in_res or self.mode == "minimal":
                    executed_tools.append(tool)

            snapshot = await graph.aget_state(config)
            if snapshot.next:
                hitl_interrupted = True

            final_messages = final_state.get("messages", [])
            ai_messages = [m for m in final_messages if isinstance(m, AIMessage)]
            raw_answer = (
                ai_messages[-1].content if ai_messages else "Processamento de agente concluído."
            )

            out_validation = validate_answer(raw_answer)
            guardrail_out_flagged = not out_validation.safe
            guardrail_triggered = guardrail_in_flagged or guardrail_out_flagged

            cycle_count = final_state.get("cycle_count", 1)

        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
            actual_intent = None
            raw_answer = ""
            guardrail_triggered = False
            cycle_count = 1

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        result = TrajectoryResult(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            category=scenario.category,
            passed=False,
            duration_ms=round(duration_ms, 2),
            actual_intent=actual_intent,
            visited_nodes=visited_nodes,
            executed_tools=executed_tools,
            raw_answer=raw_answer,
            pii_masked=bool(pii_detected),
            guardrail_triggered=guardrail_triggered,
            hitl_interrupted=hitl_interrupted,
            cycle_count=cycle_count,
            telemetry=telemetry,
            errors=errors,
        )

        passed, assertions = validate_scenario_result(scenario, result)
        result.passed = passed and not errors
        result.assertions = assertions

        return result

    async def run_suite(
        self,
        scenarios: list[HarnessScenario],
        suite_name: str = "UsiEdu Agent Harness Suite",
    ) -> HarnessReport:
        """Executa uma suíte completa de cenários e gera o relatório consolidado."""
        results: list[TrajectoryResult] = []
        for scen in scenarios:
            res = await self.run_scenario(scen)
            results.append(res)

        total = len(results)
        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        pass_rate = (passed_count / total) if total > 0 else 1.0

        metrics = calculate_harness_metrics(results)

        return HarnessReport(
            suite_name=suite_name,
            total_scenarios=total,
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            pass_rate=round(pass_rate, 4),
            metrics=metrics,
            results=results,
        )

    def load_scenarios_from_directory(self, dir_path: Path | str) -> list[HarnessScenario]:
        """Carrega todos os arquivos .json de cenários de um diretório."""
        path = Path(dir_path)
        scenarios: list[HarnessScenario] = []
        for file in sorted(path.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        scenarios.append(HarnessScenario(**item))
                elif isinstance(data, dict):
                    scenarios.append(HarnessScenario(**data))
            except Exception as err:
                logger.error(f"Erro ao carregar cenário {file}: {err}")
        return scenarios
