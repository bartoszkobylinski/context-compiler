API_PORT ?= 4865
FRONTEND_PORT ?= 4866

.PHONY: install test api frontend eval

install:
	uv sync

test:
	PYTHONPATH=. uv run pytest -q

api:
	PYTHONPATH=. uv run uvicorn backend.main:app --reload --port $(API_PORT)

frontend:
	cd frontend && python3 -m http.server $(FRONTEND_PORT)

eval:
	PYTHONPATH=. uv run python -m evals.run_eval
