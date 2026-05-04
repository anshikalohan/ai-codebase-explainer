.PHONY: help install dev test build clean docker-up docker-down

# Default
help:
	@echo ""
	@echo "  AI Codebase Explainer — Dev Commands"
	@echo "  ─────────────────────────────────────"
	@echo "  make install     Install all dependencies"
	@echo "  make dev         Run backend + frontend in dev mode"
	@echo "  make dev-back    Run backend only"
	@echo "  make dev-front   Run frontend only"
	@echo "  make test        Run backend tests"
	@echo "  make build       Build frontend for production"
	@echo "  make docker-up   Start with Docker Compose"
	@echo "  make docker-down Stop Docker Compose"
	@echo "  make clean       Remove build artifacts and caches"
	@echo ""

install:
	@echo "→ Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "→ Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ All dependencies installed"

dev-back:
	@echo "→ Starting backend on http://localhost:8000"
	cd backend && uvicorn app.main:app --reload --port 8000

dev-front:
	@echo "→ Starting frontend on http://localhost:5173"
	cd frontend && npm run dev

dev:
	@echo "→ Starting full stack..."
	@make -j2 dev-back dev-front

test:
	@echo "→ Running backend tests..."
	cd backend && pytest tests/ -v --tb=short
	@echo "✓ Tests complete"

test-cov:
	cd backend && pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "→ Coverage report at backend/htmlcov/index.html"

build:
	@echo "→ Building frontend..."
	cd frontend && npm run build
	@echo "✓ Build complete — dist/ ready"

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	@echo "→ Cleaning build artifacts..."
	rm -rf frontend/dist frontend/node_modules/.cache
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/htmlcov
	@echo "✓ Clean complete"

env-setup:
	cp backend/.env.example backend/.env
	cp frontend/.env.example frontend/.env
	@echo "✓ .env files created — add your GROQ_API_KEY to backend/.env"
