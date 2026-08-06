"""Marca o calendário para reindexação e remove seus pontos do Qdrant."""

import json

from qdrant_client import QdrantClient

# 1. Marca calendario como nao indexado no manifest
manifest = json.loads(open("knowledge_base/manifest.json", encoding="utf-8").read())
for doc in manifest["documents"]:
    if "calend" in doc["file"].lower():
        doc["indexed"] = False
        print(f"Marcado para reindexacao: {doc['file']}")
open("knowledge_base/manifest.json", "w", encoding="utf-8").write(
    json.dumps(manifest, ensure_ascii=False, indent=2)
)

# 2. Deleta pontos do calendario no Qdrant
client = QdrantClient("http://localhost:6333")
all_points, _ = client.scroll(
    collection_name="academico", limit=10000, with_payload=True, with_vectors=False
)
ids = [p.id for p in all_points if "Calend" in p.payload.get("documento", "")]
if ids:
    client.delete(collection_name="academico", points_selector=ids)
    print(f"Deletados {len(ids)} pontos do calendario no Qdrant")
else:
    print("Nenhum ponto do calendario encontrado")
