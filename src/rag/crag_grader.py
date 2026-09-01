"""Corrective RAG (CRAG) — Grader de relevância e filtragem de ruído pós-recuperação."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.observability.component_measurements import component_measurement

if TYPE_CHECKING:
    from src.rag.models import RetrievalResult

logger = logging.getLogger(__name__)


class RetrievalGrader:
    """Grader de relevância para Corrective RAG (CRAG).

    Avalia os documentos candidatos retornados pela busca/reranker e filtra
    chunks com score de relevância abaixo do limiar estipulado. Se nenhum
    documento atingir o corte, sinaliza a ausência de contexto confiável para
    que os agentes acionem uma recusa segura sem alucinações.
    """

    def __init__(
        self,
        min_relevance_score: float = 0.05,
        enabled: bool = True,
    ) -> None:
        self.min_relevance_score = min_relevance_score
        self.enabled = enabled

    def grade_results(
        self,
        query: str,
        results: list[RetrievalResult],
        min_score: float | None = None,
    ) -> tuple[list[RetrievalResult], bool]:
        """Avalia e filtra a lista de resultados recuperados.

        Args:
            query: Consulta original ou reescrita.
            results: Lista de RetrievalResult ordenados por reranking.
            min_score: Limiar customizado opcional (default usa self.min_relevance_score).

        Returns:
            Tupla (resultados_filtrados, has_relevant_context).
        """
        if not results:
            return [], False

        if not self.enabled:
            return results, True

        cutoff = min_score if min_score is not None else self.min_relevance_score

        with component_measurement(
            logger=logger,
            component="crag_grader",
            operation="grade_results",
            item_count=len(results),
            backend="score_threshold",
        ):
            approved: list[RetrievalResult] = [
                r for r in results if r.score is not None and r.score >= cutoff
            ]

        rejected_count = len(results) - len(approved)
        if rejected_count > 0:
            logger.info(
                "CRAG Grader filtrou %d documento(s) com score < %.2f para a consulta '%s'.",
                rejected_count,
                cutoff,
                query[:80],
            )

        has_relevant = len(approved) > 0
        if not has_relevant:
            logger.warning(
                "CRAG Grader: Nenhum documento atingiu o score mínimo de %.2f para a query '%s'.",
                cutoff,
                query[:80],
            )

        return approved, has_relevant
