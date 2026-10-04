"""Armazenamento vetorial serverless disk-based com LanceDB (Zero-Daemon)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import lancedb

if TYPE_CHECKING:
    from src.rag.models import Chunk

logger = logging.getLogger(__name__)


class LanceDBStore:
    """Repositório de armazenamento vetorial embarcado em disco via LanceDB."""

    def __init__(self, db_path: str | Path = "data/lancedb") -> None:
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))

    def _open_table_safe(self, table_name: str) -> Any | None:
        """Abre a tabela de forma segura ou retorna None se ela não existir."""
        try:
            return self.db.open_table(table_name)
        except (ValueError, FileNotFoundError):
            return None

    def get_or_create_table(
        self,
        table_name: str,
        initial_data: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Obtém tabela existente ou cria uma nova se initial_data for fornecido."""
        tbl = self._open_table_safe(table_name)
        if tbl is not None:
            return tbl

        if initial_data:
            return self.db.create_table(table_name, initial_data, mode="create")

        return None

    def upsert_chunks(
        self,
        table_name: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> int:
        """Insere ou atualiza chunks na tabela LanceDB.

        Args:
            table_name: Nome da tabela ('academico' ou 'institucional').
            chunks: Lista de Chunks a indexar.
            vectors: Lista de embeddings correspondentes.

        Returns:
            Número de chunks inseridos.
        """
        if not chunks:
            return 0

        records: list[dict[str, Any]] = []
        for chunk, vector in zip(chunks, vectors):
            meta = chunk.metadata or {}
            record = {
                "id": str(chunk.id),
                "vector": vector,
                "text": str(chunk.text),
                "documento": str(meta.get("documento", "")),
                "titulo": str(meta.get("titulo", "")),
                "secao": str(meta.get("secao", "") or ""),
                "publico_alvo": str(meta.get("publico_alvo", "all")),
                "instituicao": str(meta.get("instituicao", "")),
                "url_fonte": str(meta.get("url_fonte", "") or ""),
                "parent_text": str(meta.get("parent_text", "") or ""),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "total_chunks": int(meta.get("total_chunks", 0)),
            }
            records.append(record)

        tbl = self._open_table_safe(table_name)
        if tbl is None:
            self.db.create_table(table_name, records, mode="create")
            logger.info("Tabela LanceDB '%s' criada com %d registros.", table_name, len(records))
        else:
            # Idempotência: remove chunks antigos com os mesmos IDs antes de reinserir
            ids_to_replace = [r["id"] for r in records]
            if ids_to_replace:
                batch_size = 500
                for i in range(0, len(ids_to_replace), batch_size):
                    chunk_ids = ids_to_replace[i : i + batch_size]
                    formatted_ids = ", ".join(f"'{cid}'" for cid in chunk_ids)
                    try:
                        tbl.delete(f"id IN ({formatted_ids})")
                    except Exception as exc:
                        logger.debug("Falha ao deletar IDs prévios em '%s': %s", table_name, exc)
            tbl.add(records)
            logger.info("Adicionados %d registros à tabela LanceDB '%s'.", len(records), table_name)

        return len(records)

    def search_vector(
        self,
        table_name: str,
        query_vector: list[float],
        limit: int = 20,
        profile: str = "student",
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Executa busca vetorial por cosseno com filtros no LanceDB.

        Args:
            table_name: Nome da tabela.
            query_vector: Vetor da consulta.
            limit: Quantidade máxima de resultados (top-k).
            profile: Perfil do usuário ('student' ou 'staff').
            metadata_filters: Filtros opcionais adicionais (ex.: {'documento': '...'}).

        Returns:
            Lista de dicionários contendo os dados do chunk e o campo 'score'.
        """
        tbl = self._open_table_safe(table_name)
        if tbl is None:
            logger.warning("Tabela LanceDB '%s' não encontrada para busca.", table_name)
            return []

        where_clauses: list[str] = []

        if profile == "student":
            where_clauses.append("publico_alvo IN ('student', 'todos', 'both', 'all')")
        elif profile == "staff":
            where_clauses.append("publico_alvo IN ('staff', 'todos', 'both', 'all')")

        if metadata_filters:
            for k, v in metadata_filters.items():
                if v is not None:
                    safe_v = str(v).replace("'", "''")
                    where_clauses.append(f"{k} = '{safe_v}'")

        query = tbl.search(query_vector).metric("cosine").limit(limit)

        if where_clauses:
            filter_sql = " AND ".join(where_clauses)
            query = query.where(filter_sql)

        raw_results = query.to_list()

        results: list[dict[str, Any]] = []
        for r in raw_results:
            dist = float(r.get("_distance", 1.0))
            score = max(0.0, min(1.0, 1.0 - dist))

            doc = dict(r)
            doc["score"] = score
            results.append(doc)

        return results

    def get_all_documents(self, table_name: str) -> list[tuple[str, str]]:
        """Retorna todos os documentos (id, text) para construção do índice BM25."""
        tbl = self._open_table_safe(table_name)
        if tbl is None:
            return []

        arrow_table = tbl.to_arrow()
        ids = arrow_table["id"].to_pylist()
        texts = arrow_table["text"].to_pylist()

        return list(zip(ids, texts))

    def get_by_ids(self, table_name: str, ids: list[str]) -> list[dict[str, Any]]:
        """Recupera registros por lista de IDs."""
        if not ids:
            return []

        tbl = self._open_table_safe(table_name)
        if tbl is None:
            return []

        formatted_ids = ", ".join(f"'{cid}'" for cid in ids)
        try:
            arrow_table = tbl.search().where(f"id IN ({formatted_ids})").limit(len(ids)).to_arrow()
            return arrow_table.to_pylist()
        except Exception as exc:
            logger.warning("Falha ao buscar por IDs no LanceDB: %s", exc)
            return []

    def delete_document(self, table_name: str, doc_name: str) -> None:
        """Remove todos os chunks associados a um documento."""
        tbl = self._open_table_safe(table_name)
        if tbl is None:
            return

        safe_name = doc_name.replace("'", "''")
        try:
            tbl.delete(f"documento = '{safe_name}'")
            logger.info("Documento '%s' removido da tabela '%s'.", doc_name, table_name)
        except Exception as exc:
            logger.warning("Erro ao deletar documento '%s': %s", doc_name, exc)

    def has_document(self, table_name: str, doc_name: str) -> bool:
        """Verifica se há chunks indexados para determinado documento."""
        tbl = self._open_table_safe(table_name)
        if tbl is None:
            return False

        safe_name = doc_name.replace("'", "''")
        try:
            results = tbl.search().where(f"documento = '{safe_name}'").limit(1).to_list()
            return len(results) > 0
        except Exception:
            return False

    def count(self, table_name: str) -> int:
        """Retorna contagem total de registros na tabela."""
        tbl = self._open_table_safe(table_name)
        if tbl is None:
            return 0
        return tbl.count_rows()
