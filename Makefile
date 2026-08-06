# UsiEdu - Makefile para Linux/macOS
# Para Windows use: powershell -File scripts/dev.ps1

.PHONY: dev test lint format ingest api clean

dev:
	docker compose up -d qdrant
	@echo "Qdrant disponivel em http://localhost:6333"
	@if [ -f src/api/main.py ]; then \
		uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "API ainda nao implementada (Sprint 2)."; \
	fi

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

ingest:
	python -m src.rag.ingest

api:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
