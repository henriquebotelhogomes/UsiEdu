"""Teste de sanidade — verifica que o ambiente está funcional."""


def test_sanity():
    """Teste mínimo para confirmar que pytest está configurado corretamente."""
    assert 1 + 1 == 2


def test_imports():
    """Verifica que os pacotes principais são importáveis."""
    import src  # noqa: F401
    import src.agents  # noqa: F401
    import src.api  # noqa: F401
    import src.evaluation  # noqa: F401
    import src.llm  # noqa: F401
    import src.orchestration  # noqa: F401
    import src.rag  # noqa: F401
    import src.tools  # noqa: F401
