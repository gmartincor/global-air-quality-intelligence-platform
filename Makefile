.PHONY: help dev-build dev-shell dev-exec up down logs restart ps \
        format lint type-check test test-cov install-hooks verify \
        terraform-init terraform-plan terraform-apply terraform-destroy \
        clean clean-all

DOCKER_COMPOSE := docker-compose -f infrastructure/docker/docker-compose.yml
DEV_CONTAINER := air-quality-dev
COMPOSE_RUN := $(DOCKER_COMPOSE) run --rm $(DEV_CONTAINER)
COMPOSE_EXEC := $(DOCKER_COMPOSE) exec $(DEV_CONTAINER)

help:
	@echo "Global Air Quality Intelligence Platform"
	@echo "========================================"
	@echo ""
	@echo "SETUP"
	@echo "  make dev-build        Build development container"
	@echo "  make up               Start all services (detached)"
	@echo "  make down             Stop all services"
	@echo "  make restart          Restart all services"
	@echo "  make verify           Verify environment setup"
	@echo ""
	@echo "DEVELOPMENT"
	@echo "  make dev-shell        Open bash shell in dev container"
	@echo "  make dev-exec CMD=    Execute command in dev container"
	@echo "  make install-hooks    Install pre-commit hooks"
	@echo ""
	@echo "CODE QUALITY"
	@echo "  make format           Format code with black and isort"
	@echo "  make lint             Lint code with flake8"
	@echo "  make type-check       Type check with mypy"
	@echo ""
	@echo "TESTING"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "INFRASTRUCTURE"
	@echo "  make logs             View service logs (Ctrl+C to exit)"
	@echo "  make ps               Show running containers"
	@echo "  make terraform-init   Initialize Terraform"
	@echo "  make terraform-plan   Plan Terraform changes"
	@echo "  make terraform-apply  Apply Terraform configuration"
	@echo "  make terraform-destroy Destroy Terraform resources"
	@echo ""
	@echo "CLEANUP"
	@echo "  make clean            Remove generated files"
	@echo "  make clean-all        Remove all data and volumes"
	@echo ""
	@echo "SERVICE URLS (after 'make up')"
	@echo "  Airflow UI:    http://localhost:8080 (admin/admin)"
	@echo "  Spark UI:      http://localhost:8081"
	@echo "  LocalStack:    http://localhost:4566"
	@echo "  PostgreSQL:    localhost:5432 (airflow/airflow)"
	@echo "  Redis:         localhost:6379"
	@echo "========================================"

dev-build:
	@echo "Building development container..."
	$(DOCKER_COMPOSE) build dev
	@echo "✅ Development container built successfully!"

dev-shell:
	@echo "Opening shell in development container..."
	$(COMPOSE_EXEC) /bin/bash

dev-exec:
	@if [ -z "$(CMD)" ]; then \
		echo "Error: CMD parameter required. Usage: make dev-exec CMD='command'"; \
		exit 1; \
	fi
	$(COMPOSE_EXEC) /bin/bash -c "$(CMD)"

up:
	@echo "Starting all services..."
	$(DOCKER_COMPOSE) up -d
	@echo "Waiting for services to be ready..."
	@sleep 40
	@echo "✅ All services are running!"

down:
	@echo "Stopping all services..."
	$(DOCKER_COMPOSE) down
	@echo "✅ All services stopped!"

restart:
	@echo "Restarting all services..."
	$(DOCKER_COMPOSE) restart
	@echo "✅ All services restarted!"

logs:
	@echo "Showing service logs (Ctrl+C to exit)..."
	$(DOCKER_COMPOSE) logs -f

ps:
	@$(DOCKER_COMPOSE) ps

verify:
	@echo "Verifying environment setup..."
	@./scripts/verify_docker_env.sh

install-hooks:
	@echo "Installing pre-commit hooks..."
	$(COMPOSE_EXEC) poetry run pre-commit install
	@echo "✅ Pre-commit hooks installed!"

format:
	@echo "Formatting code..."
	$(COMPOSE_EXEC) poetry run black src tests
	$(COMPOSE_EXEC) poetry run isort src tests
	@echo "✅ Code formatted successfully!"

lint:
	@echo "Linting code..."
	$(COMPOSE_EXEC) poetry run flake8 src tests
	@echo "✅ Linting complete!"

type-check:
	@echo "Running type checks..."
	$(COMPOSE_EXEC) poetry run mypy src
	@echo "✅ Type checking complete!"

test:
	@echo "Running tests..."
	$(COMPOSE_EXEC) poetry run pytest tests/
	@echo "✅ Tests complete!"

test-cov:
	@echo "Running tests with coverage..."
	$(COMPOSE_EXEC) poetry run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html
	@echo "✅ Coverage report generated in htmlcov/"

terraform-init:
	@echo "Initializing Terraform..."
	cd infrastructure/terraform && terraform init
	@echo "✅ Terraform initialized!"

terraform-plan:
	@echo "Planning Terraform changes..."
	cd infrastructure/terraform && terraform plan -var-file=environments/dev.tfvars
	@echo "✅ Terraform plan complete!"

terraform-apply:
	@echo "Applying Terraform configuration..."
	cd infrastructure/terraform && terraform apply -var-file=environments/dev.tfvars -auto-approve
	@echo "✅ Infrastructure provisioned successfully!"

terraform-destroy:
	@echo "Destroying Terraform resources..."
	cd infrastructure/terraform && terraform destroy -var-file=environments/dev.tfvars -auto-approve
	@echo "✅ Infrastructure destroyed!"

clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Generated files removed!"

clean-all: clean
	@echo "Removing all Docker volumes and Terraform state..."
	$(DOCKER_COMPOSE) down -v
	rm -rf infrastructure/docker/localstack-data
	cd infrastructure/terraform && rm -rf .terraform .terraform.lock.hcl terraform.tfstate terraform.tfstate.backup
	@echo "✅ Complete cleanup done!"
