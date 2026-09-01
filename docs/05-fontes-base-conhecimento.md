# Fontes Abertas da Base de Conhecimento

> Catálogo de documentos **reais e públicos** que alimentam o RAG da UsiEdu no piloto.
> Estratégia: usar **uma única instituição real (UnB)** como a "universidade fictícia"
> da demo, garantindo consistência das regras — todos os documentos pertencem ao mesmo
> sistema normativo, sem contradições entre fontes.

---

## 1. Por que uma instituição única?

Misturar regimentos de universidades diferentes criaria regras conflitantes na mesma base
(cada uma tem prazos, artigos e procedimentos próprios) — o que geraria respostas
inconsistentes e prejudicaria a avaliação do RAG.

**Solução:** adotar a **Universidade de Brasília (UnB)** como fonte única principal.
Ela possui, publicada e acessível, **todas as categorias de documento** de que o piloto precisa:

| Categoria | Documento UnB | Link |
|---|---|---|
| Estatuto + Regimento Geral | Estatuto e Regimento Geral da UnB | https://unb.br/images/Documentos/Estatuto_e_Regimento_Geral_UnB.pdf |
| Calendário acadêmico (graduação) | Calendário Universitário de Graduação 2026.1 (PDF) | https://saa.unb.br/wp-content/uploads/2026/02/2026_1_Calend_Ativ_Grad_27_02_2026.pdf |
| Calendário acadêmico (graduação) | Calendário Universitário de Graduação 2026.2 (PDF) | https://saa.unb.br/wp-content/uploads/2026/06/2026_2_Calend_Ativ_Grad_15_06_2026.pdf |
| Calendário de matrícula | Calendário de Matrícula em Disciplina 2026.2 (PDF) | https://saa.unb.br/wp-content/uploads/2026/06/2026_2_Calend_Mat_Grad_25_06_2026.pdf |
| Página oficial de calendários | SAA/UnB — Calendário Acadêmico de Graduação | https://saa.unb.br/calendario-academico-graduacao/ |
| Orientações ao discente | SAA/UnB — Perguntas Frequentes (aproveitamentos, matrícula, trancamentos, histórico) | https://saa.unb.br/perguntas-frequentes/ |
| Guia do calouro | Guia Calouro UnB (PDF) | https://www.noticias.unb.br/images/Noticias/2015/Documentos/20150305_GuiaCalouro.pdf |
| Guia do servidor | Guia do Servidor — Decanato de Gestão de Pessoas | https://dgp.unb.br/servidor/guia-servidor |

### Guia do Servidor — páginas individuais (menu lateral)

A página principal do Guia lista os assuntos, mas o conteúdo oficial de vários deles mora em
subpáginas do DGP referenciadas pelo menu lateral — ex.: a definição de "Afastamento para
Participação em Ação de Desenvolvimento" está em `https://dgp.unb.br/afastamentos`, fora da
página principal. Todas as URLs internas do menu lateral foram curadas manualmente no
manifest (o pipeline não faz crawl; cada URL é um GET explícito). Decisões de escopo:
domínio externo `capacitacao.unb.br` excluído; todas as entradas têm `publico_alvo: staff`
e são indexadas na coleção `institucional` (ver seção 4).

| Assunto (rótulo do menu) | URL |
|---|---|
| SouGov.br | https://dgp.unb.br/sougovbr |
| Redistribuição | https://dgp.unb.br/redistribuicao |
| Movimentação Interna | https://dgp.unb.br/servidor-remocao |
| Prata, Ouro e Diamante da Casa | https://dgp.unb.br/prata-ouro-diamante |
| Formulários | https://dgp.unb.br/formularios |
| SIGRH — Sobre | https://dgp.unb.br/sigrh-sobre |
| SIGRH — Consultas | https://dgp.unb.br/sigrh-consultas |
| SIGRH — Declarações | https://dgp.unb.br/sigrh-declaracoes |
| SIGRH — Ponto Eletrônico | https://dgp.unb.br/sigrh-ponto |
| SIGRH — Ocorrências e Ausências | https://dgp.unb.br/sigrh-ocorrencias |
| SIGRH — Períodos de Recesso | https://dgp.unb.br/sigrh-recesso |
| Carreira Técnico-Administrativa | https://dgp.unb.br/perfil-tecnico |
| Carreira do Magistério Superior | https://dgp.unb.br/perfil-docente |
| Licença e Afastamentos | https://dgp.unb.br/afastamentos |
| Assistência à Saúde Suplementar | https://dgp.unb.br/assistencia-saude-menu |
| Administradora de Planos de Saúde Contratada | https://dgp.unb.br/administradora-de-planos-de-saude-contratada |
| Administradoras de Planos de Saúde | https://dgp.unb.br/plano-saude |
| Relatórios Epidemiológicos | https://dgp.unb.br/relatorio-epidemiologico |
| Perícia Oficial em Saúde | https://dgp.unb.br/pericia-oficial-em-saude |
| Pessoas com Deficiência | https://dgp.unb.br/pessoas-com-deficiencia |
| Exames Médicos Periódicos | https://dgp.unb.br/exames-medicos-periodicos |
| Equipamentos de Proteção Individual | https://dgp.unb.br/epis |

**Detecção de drift do menu:** `python -m src.rag.discover` faz fetch read-only da página do
Guia, extrai o menu lateral e compara com o manifest — exit 0 sem drift, exit 1 quando há URL
nova no menu (ou parsing vazio, que indica mudança estrutural no site). Nenhuma escrita é feita.

**Cobertura por agente:**

| Agente | Documentos UnB que o atendem |
|---|---|
| Agente Acadêmico | Regimento Geral + Calendários + Guia Calouro |
| Agente Documental | Guia do Servidor + Regimento Geral (parte administrativa) |
| Tutor / Carreira *(roadmap)* | Guia Calouro (serviços, oportunidades) |

## 2. Legislação federal (camada multinível)

Complemento comum a qualquer instituição — permite demonstrar respostas que combinam
regimento institucional + lei federal:

| Fonte | Conteúdo | Link |
|---|---|---|
| LDB — Lei nº 9.394/1996 | Diretrizes e bases da educação nacional | https://www.planalto.gov.br/ccivil_03/leis/l9394.htm |
| Lei nº 8.112/1990 | Regime jurídico dos servidores públicos federais | https://www.planalto.gov.br/ccivil_03/leis/L8112cons.htm |

## 3. Fontes secundárias *(backup/expansão — usar apenas se necessário)*

Caso algum documento da UnB fique indisponível ou se queira expandir a base:

| Categoria | Fonte | Link |
|---|---|---|
| Regimento Geral | UFS | https://www.sigrh.ufs.br/sigrh/public/documentos/ufs/0179_regimento_geral_da_ufs.pdf |
| Regimento Geral | UFABC | https://www.ufabc.edu.br/a-ufabc/documentos/regimento-geral |
| Regimento Geral | UFRJ | https://www.iq.ufrj.br/arquivos/2014/08/Regimento_Geral_1970_atualizado.pdf |
| Calendário acadêmico | UFMG | https://www.ufmg.br/a-universidade/calendario-escolar/ |
| Calendário acadêmico | UFPR | https://prograp.ufpr.br/calendario-academico/ |
| Calendário acadêmico | UFCA | https://www.ufca.edu.br/calendario-universitario/ |
| Manual do calouro | UEM | https://www.cpr.uem.br/images/2023/MANUAL-CALOURADA-2023-v3.pdf |
| Manual do calouro | Poli/UFRJ | https://poli.ufrj.br/wp-content/uploads/2021/08/Manual-dos-Calouros-21.1-2.pdf |
| Manual do servidor | UFRA | https://progep.ufra.edu.br/attachments/-01_MANUAL%20DO%20SERVIDOR.pdf |
| Código de Ética | UFC | https://comissaodeetica.ufc.br/wp-content/uploads/2021/05/codigo-de-etica-2017.pdf |
| Manual de Conduta | Governo Federal (MCom) | https://www.gov.br/mcom/pt-br/acesso-a-informacao/manualdecondutadoagentepublicocivil.pdf |

> ⚠️ Se fontes secundárias forem usadas, **indexá-las em coleção separada** ou com metadado
> `instituicao` distinto — nunca misturar regras de instituições diferentes na resposta.

## 4. Mapeamento fonte → coleção no Qdrant

| Coleção | Fontes (piloto) | Perfil com acesso |
|---|---|---|
| `academico` | Regimento UnB, Calendários UnB, Guia Calouro UnB, LDB | Estudante |
| `institucional` | Guia do Servidor UnB, Regimento UnB (parte administrativa), Lei 8.112 | Funcionário/Docente |

Metadados obrigatórios por chunk: `instituicao`, `documento`, `secao`, `pagina`, `url_fonte`, `publico_alvo`.

## 5. Boas práticas de uso

1. **Crédito**: manter a URL original nos metadados de cada chunk e citá-la nas respostas.
2. **Núcleo mínimo do piloto**: Regimento Geral da UnB + Calendário 2026.2 + Guia do Servidor.
3. **Atualização**: scripts de ingestão devem ser idempotentes (re-indexação sem duplicatas).
4. **Apresentação**: explicar ao avaliador que a UnB é usada como stand-in de uma instituição
   real — mesma engenharia e mesma dificuldade de uma base proprietária.

## 6. Fontes complementares em avaliação *(opcional)*

- Páginas públicas da própria Cruzeiro do Sul (FAQ, editais, páginas de cursos) — usariam
  conteúdo público da empresa, aumentando a aderência da demo. Avaliar volume e ruído antes.
- INEP/MEC: censos e notas técnicas públicas (para perguntas de contexto educacional).
