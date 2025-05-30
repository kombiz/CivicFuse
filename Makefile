.PHONY: help build up down logs shell test lint clean validate init

# Default target
help:
	@echo "Advocacy CMS - Available Commands"
	@echo "================================="
	@echo "Docker Commands:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View application logs"
	@echo "  make shell       - Access app container shell"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test        - Run all tests"
	@echo "  make lint        - Check code quality"
	@echo "  make validate    - Validate environment and components"
	@echo "  make clean       - Clean temporary files"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make init        - Initialize project (first time setup)"
	@echo "  make db-init     - Initialize database schema"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f app

shell:
	docker-compose exec app /bin/bash

# Development commands
test:
	docker-compose exec app pytest

test-local:
	pytest

lint:
	docker-compose exec app python scripts/check_code_quality.py

lint-local:
	python scripts/check_code_quality.py

validate:
	docker-compose exec app python scripts/validate_environment.py
	docker-compose exec app python scripts/check_progress.py

validate-local:
	python scripts/validate_environment.py
	python scripts/check_progress.py

# Setup commands
init: build db-init up
	@echo "Setup complete! Access the app at http://localhost:8000"

db-init:
	docker-compose run --rm db-init

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

# Development shortcuts
dev: up logs

restart:
	docker-compose restart app

rebuild: down build up

# Production commands
prod-up:
	docker-compose --profile production up -d

prod-down:
	docker-compose --profile production down