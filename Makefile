# ACAS Pro - Development Makefile

.PHONY: help install test lint format clean docker-build docker-run

PYTHON := python3
PIP := pip3

help:
	@echo "ACAS Pro Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make install-dev      Install with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage"
	@echo "  make lint             Run linters (flake8, mypy)"
	@echo "  make format           Format code with black"
	@echo "  make format-check     Check code formatting"
	@echo "  make security         Run security checks (bandit)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-run       Run Docker container"
	@echo "  make docker-compose   Run with docker-compose"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Clean build artifacts"
	@echo "  make clean-all        Clean everything including venv"

# Setup
install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov black flake8 mypy bandit

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/acas_pro --cov-report=html --cov-report=term

# Code Quality
lint:
	flake8 src/acas_pro --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/acas_pro --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics
	mypy src/acas_pro --ignore-missing-imports || true

format:
	black src/acas_pro tests

format-check:
	black --check src/acas_pro tests

security:
	bandit -r src/acas_pro -f json -o bandit-report.json || true
	bandit -r src/acas_pro

# Docker
docker-build:
	docker build -t acas-pro:latest .

docker-run:
	docker run -d -p 5000:5000 --env-file .env acas-pro:latest

docker-compose:
	docker-compose up -d

docker-compose-down:
	docker-compose down

# Maintenance
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/ htmlcov/

clean-all: clean
	rm -rf .venv/ venv/

# Development server
run:
	$(PYTHON) web_app.py

run-prod:
	ACAS_ENV=production $(PYTHON) wsgi.py

# Database
db-init:
	$(PYTHON) -c "from acas_pro.core.database import db; db.init_database()"

db-migrate:
	alembic upgrade head

db-backup:
	$(PYTHON) scripts/backup.py

# Documentation
docs-serve:
	@echo "API Documentation available at: http://localhost:5000/api/docs"
	@echo "Start the server with: make run"
