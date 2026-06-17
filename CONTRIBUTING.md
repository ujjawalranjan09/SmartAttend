# Contributing to SmartAttend

## Development Setup

```bash
git clone https://github.com/ujjawalranjan09/SmartAttend.git
cd SmartAttend
cp .env.example .env
docker-compose up --build -d
docker-compose exec api alembic upgrade head
```

## Running Tests

```bash
cd apps/backend
pytest tests/ -v --tb=short
```

## Code Style

- **Python:** Ruff for linting + formatting. Run `make format` before committing.
- **JavaScript:** No linter configured yet — follow existing patterns.
- **Commits:** Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`

## Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## Pull Request Process

1. Fork and create a feature branch from `main`
2. Write tests for new functionality
3. Ensure `make test` and `make lint` pass
4. Update CHANGELOG.md
5. Open PR against `main`
