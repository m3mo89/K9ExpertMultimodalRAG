.PHONY: api worker test lint typecheck web-check

api:
	.venv/bin/uvicorn k9_expert.presentation.api:app --host 127.0.0.1 --port 8000 --reload

worker:
	.venv/bin/python -m k9_expert.worker

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check backend

typecheck:
	.venv/bin/mypy

web-check:
	npm --prefix frontend run lint && npm --prefix frontend run build
