"""Contrato determinístico do corpus autorizado da T02.2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent.parent
INVENTORY_PATH = ROOT / "src" / "evaluation" / "corpus_t02_2.json"
MANIFEST_PATH = ROOT / "knowledge_base" / "manifest.json"
EVIDENCE_PATH = ROOT / "src" / "evaluation" / "evidencia_corpus_t02_2.json"
DOC_PATH = ROOT / "docs" / "profissionalizacao" / "02-qualidade-rag.md"
EXPECTED_QUESTIONS = {f"q{number:03d}" for number in range(18, 23)}
EXPECTED_STATUS = {
    "q018": "covered",
    "q019": "covered",
    "q020": "partially_covered",
    "q021": "scope_clarification_required",
    "q022": "unit_specific_only",
}
REQUIRED_SOURCE_FIELDS = {
    "id",
    "title",
    "publisher",
    "source_url",
    "file",
    "file_type",
    "publico_alvo",
    "authorized",
    "authorization_basis",
    "sha256",
    "questions",
    "evidence",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_inventario_tem_schema_ids_urls_e_cobertura_completos() -> None:
    inventory = _load(INVENTORY_PATH)

    assert set(inventory) == {
        "schema_version",
        "authorization_policy",
        "questions",
        "sources",
    }
    assert inventory["schema_version"] == "1.0.0"
    assert inventory["authorization_policy"] == (
        "Documentos publicos da UnB foram autorizados pelo proprietario do projeto."
    )
    assert set(inventory["questions"]) == EXPECTED_QUESTIONS
    assert {
        question: inventory["questions"][question]["status"] for question in EXPECTED_QUESTIONS
    } == EXPECTED_STATUS
    for question in EXPECTED_QUESTIONS:
        assert set(inventory["questions"][question]) == {"status", "finding"}
        assert inventory["questions"][question]["finding"]

    sources = inventory["sources"]
    source_ids = [source["id"] for source in sources]
    source_urls = [source["source_url"] for source in sources]
    assert len(source_ids) == len(set(source_ids))
    assert len(source_urls) == len(set(source_urls))
    assert set().union(*(set(source["questions"]) for source in sources)) == EXPECTED_QUESTIONS

    for source in sources:
        assert set(source) == REQUIRED_SOURCE_FIELDS
        assert source["authorized"] is True
        assert source["authorization_basis"] == "publico_unb_autorizado_pelo_proprietario"
        assert source["publisher"] == "Universidade de Brasilia"
        assert urlparse(source["source_url"]).scheme == "https"
        hostname = urlparse(source["source_url"]).hostname
        assert hostname == "unb.br" or hostname.endswith(".unb.br")
        assert source["file_type"] in {"pdf", "html"}
        assert source["publico_alvo"] == "staff"
        assert len(source["sha256"]) == 64
        assert set(source["sha256"]) <= set("0123456789abcdef")
        assert source["questions"] and set(source["questions"]) <= EXPECTED_QUESTIONS
        assert isinstance(source["evidence"], list) and source["evidence"]
        for evidence in source["evidence"]:
            assert set(evidence) == {"question_id", "locator", "excerpt"}
            assert evidence["question_id"] in source["questions"]
            assert all(isinstance(evidence[field], str) and evidence[field] for field in evidence)


def test_manifest_reproduz_inventario_e_checksums_dos_arquivos() -> None:
    inventory = _load(INVENTORY_PATH)
    manifest = _load(MANIFEST_PATH)
    manifest_by_file = {document["file"]: document for document in manifest["documents"]}

    for source in inventory["sources"]:
        assert source["file"] in manifest_by_file
        document = manifest_by_file[source["file"]]
        assert document["name"] == source["title"]
        assert document["url"] == source["source_url"]
        assert document["checksum"] == source["sha256"]
        assert document["publico_alvo"] == source["publico_alvo"]
        assert document["questions"] == source["questions"]
        assert document["isolated_validation"] == {
            "collection": "t02_2_corpus_20260811",
            "chunks": document["isolated_validation"]["chunks"],
            "evidence": "src/evaluation/evidencia_corpus_t02_2.json",
        }
        assert document["isolated_validation"]["chunks"] > 0

        file_path = ROOT / "knowledge_base" / source["file"]
        assert file_path.is_file()
        assert hashlib.sha256(file_path.read_bytes()).hexdigest() == source["sha256"]


def test_evidencia_comprova_ingestao_isolada_idempotente_e_recuperacao() -> None:
    inventory = _load(INVENTORY_PATH)
    manifest = _load(MANIFEST_PATH)
    manifest_by_file = {document["file"]: document for document in manifest["documents"]}
    evidence = _load(EVIDENCE_PATH)
    source_by_question = {
        question: {
            source["title"] for source in inventory["sources"] if question in source["questions"]
        }
        for question in EXPECTED_QUESTIONS
    }

    assert set(evidence) == {
        "schema_version",
        "run_id",
        "collection",
        "manifest_sha256",
        "ingestion",
        "retrieval",
    }
    assert evidence["schema_version"] == "1.0.0"
    assert evidence["collection"].startswith("t02_2_")
    assert evidence["collection"] not in {"academico", "institucional"}
    assert evidence["manifest_sha256"] == hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert evidence["ingestion"]["first_run"]["uploaded_points"] > 0
    assert set(evidence["ingestion"]["first_run"]["per_document"]) == {
        source["title"] for source in inventory["sources"]
    }
    assert all(chunks > 0 for chunks in evidence["ingestion"]["first_run"]["per_document"].values())
    for source in inventory["sources"]:
        document = manifest_by_file[source["file"]]
        assert (
            evidence["ingestion"]["first_run"]["per_document"][source["title"]]
            == document["isolated_validation"]["chunks"]
        )
    assert evidence["ingestion"]["second_run"]["uploaded_points"] == 0
    assert (
        evidence["ingestion"]["first_run"]["points_after"]
        == evidence["ingestion"]["second_run"]["points_after"]
    )

    retrieval = evidence["retrieval"]
    assert set(retrieval) == EXPECTED_QUESTIONS
    for question, result in retrieval.items():
        assert set(result) == {"question", "before", "after"}
        assert isinstance(result["before"], list)
        assert isinstance(result["after"], list) and result["after"]
        after_documents = {hit["document"] for hit in result["after"]}
        assert after_documents & source_by_question[question]
        for hit in result["after"]:
            assert set(hit) == {"document", "section", "url", "score", "excerpt"}
            assert isinstance(hit["score"], (int, float)) and not isinstance(hit["score"], bool)
            assert hit["excerpt"]


def test_status_documental_mantem_t02_2_parcial_apos_t02_3() -> None:
    document = DOC_PATH.read_text(encoding="utf-8")

    assert "| Estado | Em andamento — T02.1/T02.1b concluídas; T02.2 parcial;" in document
    assert "- [~] **T02.2 — Cobrir lacunas autorizadas do corpus**" in document
    assert "q020 permanece parcialmente coberta" in document
    assert "q021 exige identificar a secretaria" in document
    assert "q022 possui apenas regulamento de unidade" in document
    assert "- [x] **T02.3 — Definir recortes" in document
