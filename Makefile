.PHONY: install dev-install fetch serve test lint format

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

# Run the paper fetch manually (outputs JSON to stdout)
fetch:
	python -m scanner.fetch

# Start the dev server (auto-reload)
serve:
	uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

# Generate VAPID keys for Web Push (run once, copy output to .env)
vapid-keys:
	python -m server.push --generate-keys

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .
