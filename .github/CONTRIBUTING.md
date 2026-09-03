# Guia de Contribuição — UsiEdu

Agradecemos o seu interesse em contribuir para o **UsiEdu**! Este projeto segue padrões rigorosos de engenharia de software, FinOps, segurança e qualidade de IA.

---

## 🧭 Princípios e Diretrizes

1. **Protocolos de Agentes:** Leia atentamente o arquivo [AGENTS.md](../AGENTS.md) antes de propor qualquer modificação na topologia dos agentes, nos nós de consolidação ou nos guardrails.
2. **Qualidade Contínua:** Nenhuma alteração é mesclada na `main` sem passar pelos 4 Quality Gates (Linter Ruff, Pytest > 530 testes, Ragas LLM-as-a-Judge e Agent Harness).
3. **FinOps & Tokens:** Toda modificação em prompts ou ferramentas deve respeitar a poda de tokens (`trim_messages`) e a verificação no Semantic Cache.
4. **Segurança & PII:** Nenhum dado pessoal identificável (CPF, matrícula, telefone) pode trafegar sem a passagem obrigatória por `mask_pii`.

---

## 🛠️ Fluxo de Trabalho de Desenvolvimento

### 1. Criando uma Branch
Adote o padrão semântico de branch:
- `feat/nome-da-funcionalidade`
- `fix/correcao-do-bug`
- `docs/melhoria-documentacao`
- `refactor/ajuste-arquitetural`
- `test/novos-testes-unitarios`

### 2. Ambiente Local
```bash
# Clone e entre no repositório
git clone https://github.com/henriquebotelhogomes/UsiEdu.git
cd UsiEdu

# Ambiente Python
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1 | Linux: source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd frontend
npm ci
cd ..
```

### 3. Validação Pré-Commit / Pré-Push
Antes de abrir um Pull Request, execute localmente:
```bash
# 1. Checagem de Estilo e Linter
ruff check .
ruff format --check .

# 2. Testes Unitários
pytest tests/unit/

# 3. Testes do Frontend
cd frontend && npm test && npm run build && cd ..
```

---

## 📬 Abrindo um Pull Request (PR)

- Preencha todos os campos do **Pull Request Template**.
- Certifique-se de que os testes automatizados do GitHub Actions estejam todos verdes (`CI`, `Quality Gate`, `CodeQL`).
- Aguarde a revisão dos proprietários de código definidos em [CODEOWNERS](CODEOWNERS).
