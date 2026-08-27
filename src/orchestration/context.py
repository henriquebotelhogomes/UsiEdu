"""Módulo de Contexto de Ambiente e Grounding Temporal (Padrão Global / Enterprise).

Injeta automaticamente metadados de execução (data/hora UTC e local, timezone,
ambiente e perfil do usuário) em todos os agentes, seguindo o padrão de middlewares
de orquestração de plataformas como ChatGPT, Claude e Perplexity.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def get_current_datetime_br() -> datetime:
    """Retorna o datetime atual no fuso horário do Brasil (America/Sao_Paulo / UTC-3)."""
    br_tz = timezone(timedelta(hours=-3))
    return datetime.now(br_tz)


def get_system_context(profile: str = "student") -> str:
    """Gera o bloco padrão de contexto do sistema para injeção nos agentes.

    Args:
        profile: Perfil do usuário logado ('student' ou 'staff').

    Returns:
        String formatada em Markdown com os metadados de ambiente e tempo.
    """
    now = get_current_datetime_br()
    dias_semana = [
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
        "Domingo",
    ]
    meses = [
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    dia_semana = dias_semana[now.weekday()]
    mes = meses[now.month - 1]

    data_formatada = f"{now.strftime('%d/%m/%Y')} ({dia_semana}, {now.day} de {mes} de {now.year})"
    hora_formatada = now.strftime("%H:%M:%S")

    return (
        f"## Contexto do Sistema (Ambiente de Execução)\n"
        f"- **Data Atual:** {data_formatada}\n"
        f"- **Hora Atual:** {hora_formatada} (Horário de Brasília, UTC-3)\n"
        f"- **Ano / Semestre Vigente:** {now.year}.2\n"
        f"- **Perfil do Usuário Autenticado:** {profile}\n"
        f"- **Diretriz Temporal:** Use a data atual acima como referência absoluta para qualquer "
        f"pergunta sobre prazos, contagem de dias, vencimentos de boletos ou períodos acadêmicos. "
        f"Nunca solicite ao usuário a data de hoje."
    )
