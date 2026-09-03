# Security Policy — UsiEdu

## Supported Versions

O projeto UsiEdu segue uma política de suporte contínuo para a versão ativa em produção.

| Versão | Suportada | Notas |
|:---:|:---:|:---|
| 1.0.x | :white_check_mark: | Versão atual em produção (FastAPI + LangGraph + RAG Híbrido) |
| < 1.0 | :x: | Versões de pré-lançamento e protótipos de sprint |

## Reportando uma Vulnerabilidade

A segurança da informação e a privacidade de dados (LGPD / PII) são prioridades absolutas no ecossistema UsiEdu.

Se você identificou uma vulnerabilidade de segurança, falha de injeção de prompt (jailbreak), vazamento de PII ou vulnerabilidade de dependência:

1. **NÃO** abra uma issue pública.
2. Utilize o recurso nativo do GitHub: **[Report a vulnerability](https://github.com/henriquebotelhogomes/UsiEdu/security/advisories/new)** na aba **Security > Advisories**.
3. Alternativamente, entre em contato diretamente com o mantenedor responsável via e-mail ou LinkedIn listado no [README](../README.md).

### O que incluir no relatório:
- Descrição detalhada da vulnerabilidade encontrada.
- Passos para reprodução (Proof of Concept - PoC), incluindo payload enviado e rota afetada (`/chat`, `/auth`, etc.).
- Impacto potencial da falha (ex: bypass de RBAC `student` vs `staff`, vazamento de histórico, injeção).
- Sugestão de mitigação ou correção, se houver.

### Nosso Compromisso:
- Confirmação do recebimento em até **48 horas**.
- Análise e plano de contenção em até **5 dias úteis**.
- Publicação de Security Advisory com os devidos créditos após o patch ser aplicado em produção.
