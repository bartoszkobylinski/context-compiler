.PHONY: install test api eval

install:
	uv sync

test:
	PYTHONPATH=. uv run pytest -q

api:
	PYTHONPATH=. uv run uvicorn backend.main:app --reload --port 8000

eval:
	PYTHONPATH=. uv run python -m evals.run_eval
