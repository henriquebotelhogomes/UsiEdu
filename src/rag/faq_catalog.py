"""Catálogo canônico de Perguntas Frequentes (FAQ) para Semantic Cache Warmup.

Contém respostas pré-auditadas e fundamentadas nos documentos oficiais da universidade
(Regimento Geral, Calendário Acadêmico 2026.2, Guia do Servidor e LDB) para pré-aquecimento
do cache semântico no deploy.
"""

from __future__ import annotations

# ruff: noqa: E501  (linhas longas intencionais: texto de respostas do FAQ)
from typing import TypedDict


class FAQItem(TypedDict):
    profile: str
    question: str
    answer: str
    intent: str
    sources: list[dict[str, str]]


FAQ_CATALOG: list[FAQItem] = [
    # ==========================================
    # Perfil: Estudante (Regimento & Calendário)
    # ==========================================
    {
        "profile": "student",
        "question": "Como funciona o trancamento de matrícula?",
        "answer": (
            "O trancamento de matrícula pode ser total (de todas as disciplinas) ou parcial "
            "(de uma ou mais disciplinas), desde que mantido o número mínimo de créditos exigido "
            "pelo curso. A solicitação deve ser feita via sistema acadêmico dentro dos prazos "
            "estabelecidos no Calendário Universitário vigente.\n\n"
            "**Fonte:** Regimento Geral da UnB, Capítulo III (Do Regime Didático e Matrícula)."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Regimento Geral da UnB",
                "section": "Capítulo III - Da Matrícula e Trancamento",
            }
        ],
    },
    {
        "profile": "student",
        "question": "Qual é a data limite para trancamento de matrícula no semestre 2026.2?",
        "answer": (
            "Conforme o Calendário Universitário de Graduação para o segundo semestre de 2026 (2026.2), "
            "o prazo final para solicitação de trancamento total ou parcial de matrícula encerra-se "
            "impreterivelmente em **30 de setembro de 2026**.\n\n"
            "**Fonte:** Calendário de Graduação 2026.2, Seção 'Prazos Acadêmicos e Matrícula'."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Calendário de Graduação 2026.2",
                "section": "Prazos Acadêmicos e Matrícula",
            }
        ],
    },
    {
        "profile": "student",
        "question": "Quando começam e terminam as aulas do semestre 2026.2?",
        "answer": (
            "No segundo semestre de 2026 (2026.2):\n"
            "- **Início das aulas:** 17 de agosto de 2026\n"
            "- **Último dia de aulas:** 14 de dezembro de 2026\n"
            "- **Término do período letivo:** 19 de dezembro de 2026\n\n"
            "**Fonte:** Calendário de Graduação 2026.2, Seção 'Período Letivo'."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Calendário de Graduação 2026.2",
                "section": "Período Letivo",
            }
        ],
    },
    {
        "profile": "student",
        "question": "Qual o limite máximo de faltas permitido para não reprovar?",
        "answer": (
            "Para aprovação em qualquer disciplina, o estudante deve cumprir a frequência mínima "
            "obrigatória de **75% da carga horária total** da matéria. O estudante que ultrapassar "
            "25% de faltas será reprovado por falta (menção SR ou RF), independentemente das notas obtidas nas avaliações.\n\n"
            "**Fonte:** Regimento Geral da UnB, Art. 84 / LDB (Lei nº 9.394/1996, Art. 47)."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Regimento Geral da UnB",
                "section": "Artigo 84 - Da Avaliação do Rendimento Escolar e Frequência",
            }
        ],
    },
    {
        "profile": "student",
        "question": "Como solicitar aproveitamento de estudos e créditos?",
        "answer": (
            "O aproveitamento de estudos realizados em cursos de graduação da própria instituição "
            "ou de outras instituições de ensino superior reconhecidas pelo MEC deve ser solicitado "
            "junto à Coordenação de Curso, instruído com histórico escolar oficial e os planos de ensino "
            "(ementas) das disciplinas cursadas para análise de equivalência de conteúdo e carga horária (mínimo de 80% de aderência).\n\n"
            "**Fonte:** Regimento Geral da UnB, Seção 'Do Aproveitamento de Estudos'."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Regimento Geral da UnB",
                "section": "Do Aproveitamento de Estudos",
            }
        ],
    },
    {
        "profile": "student",
        "question": "Como funciona a transferência interna de curso?",
        "answer": (
            "A transferência interna de curso (mudança de habilitação ou de curso de graduação) ocorre "
            "mediante edital público semestral publicado pela Secretaria Acadêmica, sujeito à existência "
            "de vagas remanescentes e critérios de rendimento acadêmico (IRA) e afinidade entre as áreas de conhecimento.\n\n"
            "**Fonte:** Regimento Geral da UnB, Capítulo 'Da Mobilidade e Transferência Interna'."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Regimento Geral da UnB",
                "section": "Da Transferência Interna",
            }
        ],
    },
    {
        "profile": "student",
        "question": "Como solicitar revisão de prova ou de nota?",
        "answer": (
            "O estudante tem o direito de solicitar revisão de avaliação ou menção final no prazo de "
            "até **3 (três) dias úteis** após a divulgação oficial do resultado pelo professor da disciplina. "
            "O pedido deve ser fundamentado por escrito e protocolado junto à chefia do departamento responsável pela disciplina.\n\n"
            "**Fonte:** Regimento Geral da UnB, Art. 89 (Dos Recursos e Revisões de Avaliação)."
        ),
        "intent": "academico",
        "sources": [
            {
                "document": "Regimento Geral da UnB",
                "section": "Artigo 89 - Dos Recursos e Revisão de Notas",
            }
        ],
    },
    # ==========================================
    # Perfil: Staff (Guia do Servidor & Normas)
    # ==========================================
    {
        "profile": "staff",
        "question": "Como funciona a licença para capacitação do servidor?",
        "answer": (
            "Após cada quinquênio (5 anos) de efetivo exercício, o servidor público federal pode, "
            "no interesse da administração, afastar-se do exercício do cargo efetivo, com a respectiva "
            "remuneração, por até 3 (três) meses, para participar de curso de capacitação profissional devidamente aprovado.\n\n"
            "**Fonte:** Guia do Servidor UnB / Lei nº 8.112/1990, Artigo 87."
        ),
        "intent": "institucional",
        "sources": [
            {
                "document": "Guia do Servidor UnB",
                "section": "Desenvolvimento na Carreira - Licença para Capacitação",
            }
        ],
    },
    {
        "profile": "staff",
        "question": "Quais são as regras para progressão funcional por mérito?",
        "answer": (
            "A progressão funcional por mérito profissional é a mudança para o padrão de vencimento "
            "imediatamente superior a cada **18 (dezoito) meses** de efetivo exercício, desde que o servidor "
            "obtenha resultado fixado em programa de avaliação de desempenho institucional individual.\n\n"
            "**Fonte:** Guia do Servidor UnB, Seção 'Carreira e Progressão Funcional'."
        ),
        "intent": "institucional",
        "sources": [
            {
                "document": "Guia do Servidor UnB",
                "section": "Carreira e Progressão Funcional",
            }
        ],
    },
    {
        "profile": "staff",
        "question": "Como funciona o estágio probatório do servidor público?",
        "answer": (
            "Ao entrar em exercício, o servidor nomeado para cargo de provimento efetivo fica sujeito a "
            "estágio probatório por período de **36 (trinta e seis) meses**, durante o qual sua aptidão e "
            "capacidade serão objeto de avaliação para o desempenho do cargo, observados fatores como assiduidade, "
            "disciplina, capacidade de iniciativa, produtividade e responsabilidade.\n\n"
            "**Fonte:** Guia do Servidor UnB / Lei nº 8.112/1990, Artigo 20."
        ),
        "intent": "institucional",
        "sources": [
            {
                "document": "Guia do Servidor UnB",
                "section": "Admissão e Estágio Probatório",
            }
        ],
    },
    {
        "profile": "staff",
        "question": "Qual o procedimento para solicitação de diárias e passagens?",
        "answer": (
            "A solicitação de diárias e passagens para viagens a serviço ou participação em eventos acadêmicos "
            "deve ser formalizada no Sistema de Concessão de Diárias e Passagens (SCDP) com antecedência mínima "
            "de **15 (quinze) dias**, instruída com justificativa técnica de interesse institucional e aprovação da chefia imediata.\n\n"
            "**Fonte:** Guia do Servidor UnB, Seção 'Processos Administrativos e Diárias'."
        ),
        "intent": "institucional",
        "sources": [
            {
                "document": "Guia do Servidor UnB",
                "section": "Processos Administrativos e Diárias",
            }
        ],
    },
    {
        "profile": "staff",
        "question": "Quais são os deveres fundamentais do servidor público?",
        "answer": (
            "São deveres fundamentais do servidor: exercer com zelo e dedicação as atribuições do cargo, "
            "ser leal às instituições a que servir, observar as normas legais e regulamentares, cumprir as ordens "
            "superiores (exceto quando manifestamente ilegais), atender com presteza ao público e guardar sigilo sobre assuntos da repartição.\n\n"
            "**Fonte:** Guia do Servidor UnB / Lei nº 8.112/1990, Artigo 116."
        ),
        "intent": "institucional",
        "sources": [
            {
                "document": "Guia do Servidor UnB",
                "section": "Regime Disciplinar - Deveres do Servidor",
            }
        ],
    },
]
