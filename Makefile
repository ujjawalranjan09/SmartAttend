.PHONY: up down dev migrate seed test lint

# Start full stack
up:
	docker-compose up --build -d

# Stop all services
down:
	docker-compose down

# Run FastAPI in dev mode (outside Docker)
dev:
	cd apps/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run DB migrations
migrate:
	cd apps/backend && alembic upgrade head

# Rollback one migration
rollback:
	cd apps/backend && alembic downgrade -1

# Autogenerate new migration
new-migration:
	cd apps/backend && alembic revision --autogenerate -m "$(name)"

# Run tests
test:
	cd apps/backend && pytest tests/ -v --asyncio-mode=auto

# Lint + format
lint:
	cd apps/backend && ruff check . && ruff format --check .

format:
	cd apps/backend && ruff format .

# Install backend deps
install:
	cd apps/backend && pip install -r requirements.txt

# Seed demo data
seed:
	cd apps/backend && python scripts/seed_demo.py
