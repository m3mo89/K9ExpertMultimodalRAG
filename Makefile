.PHONY: api serve worker store-preview store-reset test lint typecheck web-check web-test web-e2e eval-e1 eval-e2

# One explicit root is inherited by every supported backend entry point. Override with
# `make serve K9_DATA_DIR=/tmp/k9-prueba` and use the same value for the worker.
K9_DATA_DIR ?= $(CURDIR)/data
export K9_DATA_DIR

api:
	.venv/bin/uvicorn k9_expert.presentation.api:app --host 127.0.0.1 --port 8000 --reload

serve:
	PYTHONPATH=backend/src .venv/bin/python -m k9_expert.serve

worker:
	.venv/bin/python -m k9_expert.worker

store-preview:
	.venv/bin/python -m k9_expert.store_admin --data-dir "$(K9_DATA_DIR)"

store-reset:
	.venv/bin/python -m k9_expert.store_admin --data-dir "$(K9_DATA_DIR)" --execute --confirm-store-id "$(STORE_ID)"

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
