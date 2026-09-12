.PHONY: install test api

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r backend/requirements.txt

test:
	PYTHONPATH=. pytest -q

api:
	PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
