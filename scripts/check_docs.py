"""Verifica o conteúdo real dos documentos indexados no Qdrant."""

from qdrant_client import QdrantClient

from src.rag.embedder import Embedder

client = QdrantClient("http://localhost:6333")
embedder = Embedder()


def busca(colecao: str, texto: str, limit: int = 5):
    """Busca vetorial por texto."""
    vetor = embedder.embed_query(texto)
    return client.query_points(collection_name=colecao, query=vetor, limit=limit)


print("=== Calendário 2026.2: busca 'feriado' ===")
hits = busca("academico", "feriado", 5)
for p in hits.points:
    doc = p.payload.get("documento", "?")
    print(f"  [{p.score:.3f}] {doc}: {p.payload.get('text', '')[:130]}")
    print()

print("=== Guia Servidor: busca 'laboratorio' ===")
hits = busca("institucional", "laboratorio", 5)
if not hits.points:
    print("  NENHUM resultado para 'laboratorio'")
for p in hits.points:
    print(f"  [{p.score:.3f}] {p.payload.get('text', '')[:130]}")
    print()

print("=== Calendário 2026.2: TODOS os chunks ===")
all_points, _ = client.scroll(
    collection_name="academico", limit=1000, with_payload=True, with_vectors=False
)
for p in all_points:
    doc = p.payload.get("documento", "?")
    if "Calend" in doc or "calend" in doc:
        print(f"  - {p.payload.get('text', '')[:250]}")
        print()
