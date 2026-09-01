"""Contratos de prompt que a métrica de avaliação depende.

O grader de recusa (`_avaliar_resposta`) e o roteamento do supervisor só funcionam
se os prompts prescreverem o comportamento esperado. Estes testes travam esse
vínculo: sem eles, editar um prompt pode reabrir a falha da q025 (recusa correta
pontuada 0.0) ou o roteamento de legislação geral para o agente documental.
"""

from __future__ import annotations

import pytest

from src.agents.prompts.academico import ACADEMICO_SYSTEM_PROMPT
from src.agents.prompts.documental import DOCUMENTAL_SYSTEM_PROMPT
from src.agents.prompts.financeiro import FINANCEIRO_SYSTEM_PROMPT
from src.agents.prompts.supervisor import SUPERVISOR_CONTINUE_PROMPT, SUPERVISOR_SYSTEM_PROMPT

# Frase que o grader reconhece como recusa honesta (ver _avaliar_resposta).
FRASE_CANONICA_RECUSA = "Não encontrei essa informação nos documentos oficiais"

PROMPTS_AGENTE = [
    pytest.param(ACADEMICO_SYSTEM_PROMPT, id="academico"),
    pytest.param(FINANCEIRO_SYSTEM_PROMPT, id="financeiro"),
    pytest.param(DOCUMENTAL_SYSTEM_PROMPT, id="documental"),
]


class TestContratoDeRecusa:
    """Recusa precisa de wording prescrito: sem ele o comportamento correto pontua zero."""

    @pytest.mark.parametrize("prompt", PROMPTS_AGENTE)
    def test_agente_prescreve_frase_canonica_de_recusa(self, prompt: str) -> None:
        assert FRASE_CANONICA_RECUSA in prompt

    @pytest.mark.parametrize("prompt", PROMPTS_AGENTE)
    def test_redirecionamento_de_fora_de_escopo_usa_o_verbo_do_escopo(self, prompt: str) -> None:
        """Regra de redirecionamento não pode deixar o wording a critério do modelo."""
        assert "fora do escopo" in prompt.lower()


class TestContratoDeCitacaoLiteral:
    """A resposta deve transcrever a passagem operativa, não parafraseá-la."""

    @pytest.mark.parametrize("prompt", PROMPTS_AGENTE)
    def test_agente_exige_transcricao_literal_da_passagem(self, prompt: str) -> None:
        assert "transcreva literalmente" in prompt.lower()


class TestContratoDeExemploJson:
    """O exemplo de saída é imitado pelo modelo: se não for JSON válido, a rota se perde."""

    def test_formato_de_saida_do_supervisor_nao_usa_chaves_duplas(self) -> None:
        rendered = SUPERVISOR_SYSTEM_PROMPT.format(system_context="ctx", messages="hist")
        exemplo = rendered.split("## Formato de saída (JSON)")[-1]
        assert "{{" not in exemplo and "}}" not in exemplo, (
            "exemplo com {{ }} não é JSON parseável e o nó cai em fallback silencioso"
        )

    def test_formato_de_saida_do_continue_nao_usa_chaves_duplas(self) -> None:
        rendered = SUPERVISOR_CONTINUE_PROMPT.format(
            agent_result="res", messages="hist"
        )
        assert "{{" not in rendered and "}}" not in rendered
