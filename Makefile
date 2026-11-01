.PHONY: api serve worker test lint typecheck web-check web-test web-e2e eval-e1 eval-e2

api:
	.venv/bin/uvicorn k9_expert.presentation.api:app --host 127.0.0.1 --port 8000 --reload

serve:
	PYTHONPATH=backend/src .venv/bin/python -m k9_expert.serve

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

web-test:
	npm --prefix frontend test

web-e2e:
	npm --prefix frontend run test:e2e

eval-e1:
	PYTHONPATH=backend/src .venv/bin/python -m k9_expert.evaluation run --experiment E1

eval-e2:
	PYTHONPATH=backend/src .venv/bin/python -m k9_expert.evaluation run --experiment E2
