"""Testes do Agente Acadêmico e ferramentas mockadas."""

from __future__ import annotations

import pytest

from src.agents.academico import _executar_ferramentas_academicas
from src.tools.academico_tools import get_faltas, get_notas
from src.tools.mock_data import BOLETOS, POLITICA_RENEGOCIACAO, STUDENTS, USUARIOS_DEMO


class TestMockData:
    """Testes dos dados mockados."""

    def test_students_tem_ana(self) -> None:
        """Ana Souza deve estar nos dados mockados."""
        assert "ana-123" in STUDENTS
        assert STUDENTS["ana-123"]["nome"] == "Ana Souza"

    def test_ana_tem_notas(self) -> None:
        """Ana deve ter notas em calculo-1 e programacao-1."""
        notas = STUDENTS["ana-123"]["notas"]
        assert "calculo-1" in notas
        assert "programacao-1" in notas

    def test_ana_tem_faltas(self) -> None:
        """Ana deve ter faltas registradas."""
        faltas = STUDENTS["ana-123"]["faltas"]
        assert "calculo-1" in faltas
        assert faltas["calculo-1"] == 6

    def test_boletos_ana_tem_um_vencido(self) -> None:
        """Ana deve ter um boleto vencido."""
        assert len(BOLETOS["ana-123"]) == 1
        assert BOLETOS["ana-123"][0]["status"] == "vencido"

    def test_politica_renegociacao_tem_desconto(self) -> None:
        """Política de renegociação deve ter desconto máximo."""
        assert POLITICA_RENEGOCIACAO["desconto_maximo_percentual"] == 10

    def test_usuarios_demo_tem_ana_e_carlos(self) -> None:
        """Usuários demo deve ter ana e carlos."""
        assert "ana@demo.usiedu" in USUARIOS_DEMO
        assert "carlos@demo.usiedu" in USUARIOS_DEMO
        assert USUARIOS_DEMO["ana@demo.usiedu"]["profile"] == "student"
        assert USUARIOS_DEMO["carlos@demo.usiedu"]["profile"] == "staff"


class TestAcademicTools:
    """Testes das ferramentas acadêmicas."""

    @pytest.mark.asyncio
    async def test_get_notas_ana(self) -> None:
        """Ana deve ter notas em 2 disciplinas."""
        notas = await get_notas("ana-123")
        assert len(notas) == 2
        assert notas["calculo-1"] == 5.8

    @pytest.mark.asyncio
    async def test_get_notas_aluno_inexistente(self) -> None:
        """Aluno inexistente deve retornar dict vazio."""
        notas = await get_notas("inexistente")
        assert notas == {}

    @pytest.mark.asyncio
    async def test_get_faltas_ana_calculo(self) -> None:
        """Ana deve ter 6 faltas em calculo-1."""
        faltas = await get_faltas("ana-123", "calculo-1")
        assert faltas == 6

    @pytest.mark.asyncio
    async def test_get_faltas_ana_programacao(self) -> None:
        """Ana deve ter 0 faltas em programacao-1."""
        faltas = await get_faltas("ana-123", "programacao-1")
        assert faltas == 0

    @pytest.mark.asyncio
    async def test_get_faltas_ana_todas(self) -> None:
        """Sem disciplina, deve retornar dict com todas."""
        todas = await get_faltas("ana-123")
        assert isinstance(todas, dict)
        assert len(todas) == 2

    @pytest.mark.asyncio
    async def test_get_faltas_aluno_inexistente(self) -> None:
        """Aluno inexistente deve retornar 0."""
        faltas = await get_faltas("inexistente", "calculo-1")
        assert faltas == 0


class TestExecutarFerramentasAcademicas:
    """Testes da função que executa ferramentas conforme a consulta."""

    @pytest.mark.asyncio
    async def test_consulta_notas_retorna_notas(self) -> None:
        """Consulta mencionando notas deve retornar dados de notas."""
        resultado = await _executar_ferramentas_academicas(
            "ana@demo.usiedu", "Quero ver minhas notas"
        )
        assert "Notas" in resultado
        assert "calculo-1" in resultado

    @pytest.mark.asyncio
    async def test_consulta_faltas_retorna_faltas(self) -> None:
        """Consulta mencionando faltas deve retornar dados de faltas."""
        resultado = await _executar_ferramentas_academicas(
            "ana@demo.usiedu", "Quantas faltas tenho em calculo-1"
        )
        assert "Faltas" in resultado
        assert "calculo-1" in resultado

    @pytest.mark.asyncio
    async def test_consulta_sem_palavras_chave_retorna_vazio(self) -> None:
        """Consulta sem palavras-chave deve retornar mensagem informativa."""
        resultado = await _executar_ferramentas_academicas(
            "ana@demo.usiedu", "Qual o horário de funcionamento"
        )
        assert "Nenhuma ferramenta relevante" in resultado

    @pytest.mark.asyncio
    async def test_usuario_inexistente_retorna_erro(self) -> None:
        """Usuário não encontrado deve retornar mensagem de erro."""
        resultado = await _executar_ferramentas_academicas(
            "inexistente@test.com", "Quero minhas notas"
        )
        assert "não encontrado" in resultado

    @pytest.mark.asyncio
    async def test_perfil_staff_sem_aluno_id(self) -> None:
        """Staff sem aluno_id deve retornar mensagem adequada."""
        resultado = await _executar_ferramentas_academicas(
            "carlos@demo.usiedu", "Quero minhas notas"
        )
        assert "não possui dados acadêmicos" in resultado


class TestSystemContext:
    """Testes do gerador de contexto de sistema (Enterprise Grounding)."""

    def test_get_system_context_student(self) -> None:
        """get_system_context para perfil student deve conter data e timezone."""
        from src.orchestration.context import get_system_context

        ctx = get_system_context("student")
        assert "Contexto do Sistema (Ambiente de Execução)" in ctx
        assert "Data Atual:" in ctx
        assert "Horário de Brasília" in ctx
        assert "Perfil do Usuário Autenticado:** student" in ctx
        assert "Diretriz Temporal:" in ctx

    def test_get_system_context_staff(self) -> None:
        """get_system_context para perfil staff deve conter metadados corretos."""
        from src.orchestration.context import get_system_context

        ctx = get_system_context("staff")
        assert "Perfil do Usuário Autenticado:** staff" in ctx
