"""Contratos de telemetria sanitizada dos componentes RAG da T05.2."""

from __future__ import annotations

import json
import logging

from src.observability.component_measurements import component_measurement
from src.observability.logging import JSONFormatter


def _render_measurement_record(record: logging.LogRecord) -> dict:
    return json.loads(JSONFormatter().format(record))


def test_component_measurement_logs_success_without_content_or_vectors(monkeypatch) -> None:
    records: list[logging.LogRecord] = []

    class CapturingLogger:
        def info(self, _message: str, *, extra: dict) -> None:
            record = logging.LogRecord(
                "usiedu.performance", logging.INFO, __file__, 1, _message, (), None
            )
            for key, value in extra.items():
                setattr(record, key, value)
            records.append(record)

        def warning(self, _message: str, *, extra: dict) -> None:
            raise AssertionError(f"unexpected warning: {extra}")

    monkeypatch.setattr(
        "src.observability.component_measurements.time.perf_counter", iter([1.0, 1.25]).__next__
    )

    with component_measurement(
        logger=CapturingLogger(),
        component="embedder",
        operation="encode_batch",
        item_count=3,
        backend="fastembed",
    ):
        pass

    rendered = _render_measurement_record(records[0])
    assert rendered["component"] == "embedder"
    assert rendered["operation"] == "encode_batch"
    assert rendered["outcome"] == "success"
    assert rendered["duration_ms"] == 250.0
    assert rendered["item_count"] == 3
    assert "query" not in rendered
    assert "document" not in rendered
    assert "vector" not in rendered


def test_component_measurement_logs_failure_without_exception_detail(monkeypatch) -> None:
    records: list[logging.LogRecord] = []

    class CapturingLogger:
        def info(self, _message: str, *, extra: dict) -> None:
            raise AssertionError(f"unexpected info: {extra}")

        def warning(self, _message: str, *, extra: dict) -> None:
            record = logging.LogRecord(
                "usiedu.performance", logging.WARNING, __file__, 1, _message, (), None
            )
            for key, value in extra.items():
                setattr(record, key, value)
            records.append(record)

    monkeypatch.setattr(
        "src.observability.component_measurements.time.perf_counter", iter([2.0, 2.5]).__next__
    )

    try:
        with component_measurement(
            logger=CapturingLogger(),
            component="reranker",
            operation="predict",
            item_count=5,
            backend="cross_encoder",
        ):
            raise RuntimeError("sensitive query and document")
    except RuntimeError:
        pass
    else:
        raise AssertionError("component error must propagate")

    rendered = _render_measurement_record(records[0])
    assert rendered["component"] == "reranker"
    assert rendered["operation"] == "predict"
    assert rendered["outcome"] == "error"
    assert rendered["duration_ms"] == 500.0
    assert "sensitive" not in json.dumps(rendered)
