"""Gerador de Dataset Sintético de Testes para Avaliação RAG e Ragas.

Lê os documentos da knowledge_base/ (PDFs e HTMLs) e gera automaticamente
perguntas de teste balanceadas (diretas, multi-contexto, raciocínio e fora de escopo)
com gabaritos fundamentados para avaliação contínua.

Uso:
    python scripts/generate_synthetic_testset.py --count 50
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from pathlib import Path

# Adiciona a raiz ao sys.path
raiz = Path(__file__).resolve().parent.parent
if str(raiz) not in sys.path:
    sys.path.insert(0, str(raiz))

from src.rag.chunker import DocumentChunker
from src.rag.models import Chunk, DocumentMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE_BASE = Path("knowledge_base")
DEFAULT_OUTPUT = Path("src/evaluation/synthetic_testset.jsonl")

# Perguntas plausíveis para categorias fora de escopo / sem resposta institucional
OUT_OF_SCOPE_TEMPLATES = [
    (
        "Qual a previsão do tempo para os próximos dias no campus Darcy Ribeiro?",
        "Essa pergunta está fora do escopo da plataforma. Posso orientar dúvidas acadêmicas.",
        "fora_de_escopo",
    ),
    (
        "Qual o melhor restaurante por quilo próximo à universidade?",
        "Essa pergunta está fora do escopo da plataforma. O foco é institucional e acadêmico.",
        "fora_de_escopo",
    ),
    (
        "Qual a cotação do euro e do dólar comercial hoje?",
        "Essa informação está fora do escopo do sistema de suporte universitário.",
        "fora_de_escopo",
    ),
    (
        "Como funciona a concessão de passaporte para viagens turísticas?",
        "Não encontrei essa informação nos documentos. O pedido deve ser feito na PF.",
        "fora_de_escopo",
    ),
    (
        "Qual a política institucional para reserva de vagas de estacionamento VIP?",
        "Não encontrei essa informação nos regulamentos. Consulte a prefeitura do campus.",
        "sem_resposta",
    ),
]


class SyntheticTestsetGenerator:
    """Gerador sintético de datasets de teste com distribuição de dificuldades."""

    def __init__(
        self,
        knowledge_base_dir: Path = DEFAULT_KNOWLEDGE_BASE,
        chunk_max_chars: int = 1500,
        chunk_overlap_chars: int = 200,
    ) -> None:
        self.knowledge_base_dir = knowledge_base_dir
        self.chunker = DocumentChunker(
            max_chars=chunk_max_chars,
            overlap_chars=chunk_overlap_chars,
            contextualize=False,
        )

    def load_chunks(self) -> list[Chunk]:
        """Carrega e fatia todos os documentos do manifest da base de conhecimento."""
        all_chunks: list[Chunk] = []
        manifest_path = self.knowledge_base_dir / "manifest.json"

        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for doc_entry in manifest.get("documents", []):
                    file_path = self.knowledge_base_dir / doc_entry["file"]
                    if not file_path.exists():
                        continue

                    metadata = DocumentMetadata(
                        instituicao=doc_entry.get("instituicao", "UnB"),
                        documento=doc_entry.get("name", file_path.stem),
                        publico_alvo=doc_entry.get("publico_alvo", "student"),
                        url_fonte=doc_entry.get("url", ""),
                        file_type=doc_entry.get("file_type", file_path.suffix.lstrip(".")),
                    )
                    try:
                        chunks = self.chunker.chunk_document(file_path, metadata)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        logger.warning("Falha ao fatiar '%s': %s", file_path.name, e)
            except Exception as e:
                logger.warning("Erro ao ler manifest.json: %s", e)

        # Fallback caso manifest não exista
        if not all_chunks and self.knowledge_base_dir.exists():
            for file_path in self.knowledge_base_dir.iterdir():
                if file_path.suffix.lower() in (".pdf", ".html", ".htm", ".txt"):
                    metadata = DocumentMetadata(
                        instituicao="UnB",
                        documento=file_path.stem.replace("_", " ").title(),
                        publico_alvo="student",
                        url_fonte="",
                        file_type=file_path.suffix.lstrip("."),
                    )
                    try:
                        chunks = self.chunker.chunk_document(file_path, metadata)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        logger.warning("Falha ao fatiar '%s': %s", file_path.name, e)

        logger.info("Carregados %d chunks a partir da knowledge_base.", len(all_chunks))
        return all_chunks

    def generate_testset(
        self,
        chunks: list[Chunk],
        count: int = 50,
        seed: int = 42,
    ) -> list[dict]:
        """Gera dataset balanceado: direct, reasoning, multi_context e fora de escopo."""
        if not chunks:
            logger.error("Nenhum chunk disponível para geração de testes.")
            return []

        random.seed(seed)

        # Metas de distribuição proporcionais
        n_out_of_scope = max(1, int(count * 0.10))
        n_multi_context = max(1, int(count * 0.20))
        n_reasoning = max(1, int(count * 0.30))
        n_direct = max(1, count - (n_out_of_scope + n_multi_context + n_reasoning))

        dataset: list[dict] = []
        item_id = 1

        # 1. Perguntas Diretas (Direct)
        sample_size = max(0, min(n_direct, len(chunks)))
        direct_samples = random.sample(chunks, sample_size) if sample_size > 0 else []
        for chunk in direct_samples:
            entry = self._build_direct_question(chunk, item_id)
            if entry:
                dataset.append(entry)
                item_id += 1

        # 2. Perguntas de Raciocínio (Reasoning)
        reasoning_samples = random.sample(chunks, min(n_reasoning, len(chunks)))
        for chunk in reasoning_samples:
            entry = self._build_reasoning_question(chunk, item_id)
            if entry:
                dataset.append(entry)
                item_id += 1

        # 3. Perguntas Multi-Contexto (Multi-Context)
        docs_map: dict[str, list[Chunk]] = {}
        for c in chunks:
            doc_name = c.metadata.get("documento", "")
            docs_map.setdefault(doc_name, []).append(c)

        multi_generated = 0
        for doc_chunks in docs_map.values():
            if len(doc_chunks) >= 2 and multi_generated < n_multi_context:
                c1, c2 = random.sample(doc_chunks, 2)
                entry = self._build_multi_context_question(c1, c2, item_id)
                if entry:
                    dataset.append(entry)
                    item_id += 1
                    multi_generated += 1

        # 4. Perguntas Fora de Escopo / Sem Resposta
        for q, ref, cat in OUT_OF_SCOPE_TEMPLATES[:n_out_of_scope]:
            dataset.append(
                {
                    "id": f"synth_{item_id:03d}",
                    "profile": random.choice(["student", "staff"]),
                    "user_id": "ana@demo.usiedu",
                    "question": q,
                    "reference_answer": ref,
                    "category": cat,
                    "documents": [],
                }
            )
            item_id += 1

        # Completa se necessário para atingir a meta
        while len(dataset) < count:
            chunk = random.choice(chunks)
            entry = self._build_direct_question(chunk, item_id)
            if entry:
                dataset.append(entry)
                item_id += 1

        return dataset[:count]

    def _build_direct_question(self, chunk: Chunk, item_id: int) -> dict:
        """Cria pergunta direta a partir de um chunk."""
        doc = chunk.metadata.get("documento", "Regimento")
        section = chunk.metadata.get("secao", "")
        profile = chunk.metadata.get("publico_alvo", "student")
        profile = "staff" if profile == "staff" else "student"

        text_clean = chunk.text.strip().replace("\n", " ")
        art_match = re.search(r"(Art\.\s*\d+[^—\.\n]*)", text_clean)
        first_sentence = text_clean.split(". ")[0] if ". " in text_clean else text_clean[:120]

        if art_match:
            art_str = art_match.group(1).strip()
            question = f"O que estabelece o {art_str} do documento '{doc}'?"
        elif section and section not in ("documento", "preâmbulo"):
            question = f"Quais são as disposições sobre '{section}' presentes no '{doc}'?"
        else:
            topic = first_sentence[:80].strip()
            question = f"De acordo com o '{doc}', quais são as regras sobre {topic}?"

        ref_answer = (
            f"Conforme o documento '{doc}'"
            + (f" ({section})" if section and section != "documento" else "")
            + f": {first_sentence}."
        )

        return {
            "id": f"synth_{item_id:03d}",
            "profile": profile,
            "user_id": "carlos@demo.usiedu" if profile == "staff" else "ana@demo.usiedu",
            "question": question,
            "reference_answer": ref_answer,
            "category": "direct",
            "documents": [doc],
        }

    def _build_reasoning_question(self, chunk: Chunk, item_id: int) -> dict:
        """Cria pergunta de raciocínio a partir de um chunk."""
        doc = chunk.metadata.get("documento", "Regulamento")
        section = chunk.metadata.get("secao", "")
        profile = chunk.metadata.get("publico_alvo", "student")
        profile = "staff" if profile == "staff" else "student"

        text_clean = chunk.text.strip().replace("\n", " ")
        first_sentence = text_clean.split(". ")[0] if ". " in text_clean else text_clean[:120]

        actor = "um servidor" if profile == "staff" else "um estudante"
        sec_label = section or "normas gerais"
        question = (
            f"Caso {actor} precise cumprir os requisitos de '{sec_label}' "
            f"segundo o '{doc}', quais critérios devem ser observados?"
        )

        ref_answer = (
            f"Segundo o '{doc}', {first_sentence}. "
            f"Portanto, {actor} deve observar os critérios estipulados na norma."
        )

        return {
            "id": f"synth_{item_id:03d}",
            "profile": profile,
            "user_id": "carlos@demo.usiedu" if profile == "staff" else "ana@demo.usiedu",
            "question": question,
            "reference_answer": ref_answer,
            "category": "reasoning",
            "documents": [doc],
        }

    def _build_multi_context_question(self, chunk1: Chunk, chunk2: Chunk, item_id: int) -> dict:
        """Cria pergunta combinada cruzando 2 seções."""
        doc1 = chunk1.metadata.get("documento", "")
        doc2 = chunk2.metadata.get("documento", "")
        sec1 = chunk1.metadata.get("secao", "Seção A")
        sec2 = chunk2.metadata.get("secao", "Seção B")

        profile = "student"
        is_staff = (
            chunk1.metadata.get("publico_alvo") == "staff"
            or chunk2.metadata.get("publico_alvo") == "staff"
        )
        if is_staff:
            profile = "staff"

        question = (
            f"Como o '{doc1}' articula as regras de '{sec1}' com as diretrizes de '{sec2}'"
            + (f" do '{doc2}'?" if doc1 != doc2 else "?")
        )

        ref1 = chunk1.text.split(". ")[0] if ". " in chunk1.text else chunk1.text[:100]
        ref2 = chunk2.text.split(". ")[0] if ". " in chunk2.text else chunk2.text[:100]

        ref_answer = (
            f"Em relação a '{sec1}', estabelece-se que {ref1.strip()}. "
            f"Para '{sec2}', define-se que {ref2.strip()}."
        )

        docs = list({d for d in [doc1, doc2] if d})

        return {
            "id": f"synth_{item_id:03d}",
            "profile": profile,
            "user_id": "carlos@demo.usiedu" if profile == "staff" else "ana@demo.usiedu",
            "question": question,
            "reference_answer": ref_answer,
            "category": "multi_context",
            "documents": docs,
        }

    def save_testset(self, dataset: list[dict], output_path: Path) -> None:
        """Salva o dataset em formato JSONL."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        logger.info("Dataset sintético salvo: %s (%d itens)", output_path, len(dataset))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Geração Sintética de Testes para Avaliação Ragas / RAG (Item 5)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Quantidade de casos de teste a gerar (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"Caminho de saída para o JSONL (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--knowledge-base",
        type=str,
        default=str(DEFAULT_KNOWLEDGE_BASE),
        help=f"Diretório da base de conhecimento (default: {DEFAULT_KNOWLEDGE_BASE})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed para amostragem (default: 42)",
    )

    args = parser.parse_args()

    generator = SyntheticTestsetGenerator(
        knowledge_base_dir=Path(args.knowledge_base),
    )

    chunks = generator.load_chunks()
    if not chunks:
        logger.error("Nenhum chunk carregado.")
        sys.exit(1)

    testset = generator.generate_testset(
        chunks=chunks,
        count=args.count,
        seed=args.seed,
    )

    output_path = Path(args.output)
    generator.save_testset(testset, output_path)

    categories: dict[str, int] = {}
    for item in testset:
        categories[item["category"]] = categories.get(item["category"], 0) + 1

    print("\n" + "=" * 50)
    print(f"Resumo do Dataset Sintetico Gerado ({len(testset)} itens):")
    for cat, total in sorted(categories.items()):
        print(f"  * {cat.ljust(15)}: {total:2d} ({total/len(testset)*100:.0f}%)")
    print(f"Arquivo gerado: {output_path}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
