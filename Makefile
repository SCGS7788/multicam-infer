# =============================================================================
# kvs-infer: Multi-camera inference pipeline Makefile
# =============================================================================

# Variables
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTHON_VENV := $(VENV_BIN)/python

# Docker variables
DOCKER := docker
DOCKER_COMPOSE := docker-compose
IMG ?= kvs-infer:latest
PLATFORM := linux/amd64

# Configuration
CONFIG ?= config/cameras.yaml
HTTP_PORT ?= 8080
GPU ?= 0
REGION ?= us-east-1

# AWS
AWS_PROFILE ?= default
AWS_ACCESS_KEY_ID ?= $(shell echo $$AWS_ACCESS_KEY_ID)
AWS_SECRET_ACCESS_KEY ?= $(shell echo $$AWS_SECRET_ACCESS_KEY)
AWS_SESSION_TOKEN ?= $(shell echo $$AWS_SESSION_TOKEN)

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

.DEFAULT_GOAL := help

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)kvs-infer Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-30s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make venv"
	@echo "  make run-local CONFIG=./config/cameras.yaml"
	@echo "  make docker-build IMG=123456789012.dkr.ecr.us-east-1.amazonaws.com/kvs-infer:latest"
	@echo "  make docker-run GPU=0 CONFIG=./config/cameras.yaml REGION=us-east-1"
	@echo "  make docker-compose-up"

# =============================================================================
# Local Development
# =============================================================================

.PHONY: venv
venv: ## Create Python virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Virtual environment created at ./$(VENV)$(NC)"
	@echo "$(YELLOW)Activate with: source $(VENV)/bin/activate$(NC)"

.PHONY: venv-dev
venv-dev: venv ## Create venv with development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install pytest pytest-cov pytest-mock black flake8 mypy
	@echo "$(GREEN)✓ Development environment ready$(NC)"

.PHONY: install
install: venv ## Install package in development mode
	@echo "$(BLUE)Installing kvs-infer in development mode...$(NC)"
	$(PIP) install -e .
	@echo "$(GREEN)✓ Package installed$(NC)"

.PHONY: clean-venv
clean-venv: ## Remove virtual environment
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	rm -rf $(VENV)
	@echo "$(GREEN)✓ Virtual environment removed$(NC)"

# =============================================================================
# Run Locally
# =============================================================================

.PHONY: run-local
run-local: ## Run app locally (make run-local CONFIG=./config/cameras.yaml)
	@if [ ! -f "$(CONFIG)" ]; then \
		echo "$(RED)✗ Config file not found: $(CONFIG)$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running kvs-infer locally...$(NC)"
	@echo "$(YELLOW)Config: $(CONFIG)$(NC)"
	@echo "$(YELLOW)HTTP Port: $(HTTP_PORT)$(NC)"
	@echo "$(YELLOW)AWS Region: $(REGION)$(NC)"
	AWS_REGION=$(REGION) LOG_LEVEL=INFO \
		$(PYTHON) -m src.kvs_infer.app \
		--config $(CONFIG) \
		--http 0.0.0.0:$(HTTP_PORT)

.PHONY: run-venv
run-venv: ## Run app in virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(RED)✗ Virtual environment not found. Run 'make venv' first.$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f "$(CONFIG)" ]; then \
		echo "$(RED)✗ Config file not found: $(CONFIG)$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running kvs-infer in virtual environment...$(NC)"
	@echo "$(YELLOW)Config: $(CONFIG)$(NC)"
	@echo "$(YELLOW)HTTP Port: $(HTTP_PORT)$(NC)"
	AWS_REGION=$(REGION) LOG_LEVEL=INFO \
		$(PYTHON_VENV) -m kvs_infer.app \
		--config $(CONFIG) \
		--http 0.0.0.0:$(HTTP_PORT)

# =============================================================================
# Docker Build
# =============================================================================

.PHONY: docker-build
docker-build: ## Build Docker image (make docker-build IMG=<ecr-repo>/kvs-infer:latest)
	@echo "$(BLUE)Building Docker image: $(IMG)$(NC)"
	$(DOCKER) build \
		--platform $(PLATFORM) \
		-t $(IMG) \
		-f Dockerfile \
		.
	@echo "$(GREEN)✓ Docker image built: $(IMG)$(NC)"

.PHONY: docker-build-no-cache
docker-build-no-cache: ## Build Docker image without cache
	@echo "$(BLUE)Building Docker image (no cache): $(IMG)$(NC)"
	$(DOCKER) build \
		--platform $(PLATFORM) \
		--no-cache \
		-t $(IMG) \
		-f Dockerfile \
		.
	@echo "$(GREEN)✓ Docker image built: $(IMG)$(NC)"

# =============================================================================
# Docker Run (GPU)
# =============================================================================

.PHONY: docker-run
docker-run: ## Run Docker container with GPU (make docker-run GPU=0 CONFIG=./config/cameras.yaml)
	@if [ ! -f "$(CONFIG)" ]; then \
		echo "$(RED)✗ Config file not found: $(CONFIG)$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running Docker container with GPU $(GPU)...$(NC)"
	@echo "$(YELLOW)Image: $(IMG)$(NC)"
	@echo "$(YELLOW)Config: $(CONFIG)$(NC)"
	@echo "$(YELLOW)HTTP Port: $(HTTP_PORT)$(NC)"
	@echo "$(YELLOW)AWS Region: $(REGION)$(NC)"
	$(DOCKER) run \
		--gpus '"device=$(GPU)"' \
		--runtime=nvidia \
		-p $(HTTP_PORT):8080 \
		-v $(PWD)/$(CONFIG):/app/config/cameras.yaml:ro \
		-v $(PWD)/models:/app/models:ro \
		-e AWS_REGION=$(REGION) \
		-e AWS_DEFAULT_REGION=$(REGION) \
		-e AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
		-e AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
		-e AWS_SESSION_TOKEN=$(AWS_SESSION_TOKEN) \
		-e LOG_LEVEL=INFO \
		-e CUDA_VISIBLE_DEVICES=$(GPU) \
		--name kvs-infer \
		--rm \
		$(IMG)

.PHONY: docker-run-daemon
docker-run-daemon: ## Run Docker container as daemon (background)
	@if [ ! -f "$(CONFIG)" ]; then \
		echo "$(RED)✗ Config file not found: $(CONFIG)$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running Docker container as daemon...$(NC)"
	$(DOCKER) run \
		--gpus '"device=$(GPU)"' \
		--runtime=nvidia \
		-d \
		-p $(HTTP_PORT):8080 \
		-v $(PWD)/$(CONFIG):/app/config/cameras.yaml:ro \
		-v $(PWD)/models:/app/models:ro \
		-e AWS_REGION=$(REGION) \
		-e AWS_DEFAULT_REGION=$(REGION) \
		-e AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
		-e AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
		-e LOG_LEVEL=INFO \
		-e CUDA_VISIBLE_DEVICES=$(GPU) \
		--name kvs-infer \
		$(IMG)
	@echo "$(GREEN)✓ Container started: kvs-infer$(NC)"
	@echo "$(YELLOW)Check logs: make docker-logs$(NC)"

.PHONY: docker-stop
docker-stop: ## Stop running container
	@echo "$(YELLOW)Stopping container: kvs-infer$(NC)"
	$(DOCKER) stop kvs-infer || true
	@echo "$(GREEN)✓ Container stopped$(NC)"

.PHONY: docker-logs
docker-logs: ## Show container logs
	$(DOCKER) logs -f kvs-infer

.PHONY: docker-shell
docker-shell: ## Open shell in running container
	$(DOCKER) exec -it kvs-infer /bin/bash

# =============================================================================
# Docker Compose (CPU-only for local testing)
# =============================================================================

.PHONY: docker-compose-up
docker-compose-up: ## Start services with docker-compose (CPU-only)
	@echo "$(BLUE)Starting services with docker-compose...$(NC)"
	CONFIG=$(CONFIG) REGION=$(REGION) HTTP_PORT=$(HTTP_PORT) \
		$(DOCKER_COMPOSE) up

.PHONY: docker-compose-up-build
docker-compose-up-build: ## Build and start services with docker-compose
	@echo "$(BLUE)Building and starting services...$(NC)"
	CONFIG=$(CONFIG) REGION=$(REGION) HTTP_PORT=$(HTTP_PORT) \
		$(DOCKER_COMPOSE) up --build

.PHONY: docker-compose-daemon
docker-compose-daemon: ## Start services in background
	@echo "$(BLUE)Starting services in background...$(NC)"
	CONFIG=$(CONFIG) REGION=$(REGION) HTTP_PORT=$(HTTP_PORT) \
		$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(YELLOW)Check logs: make docker-compose-logs$(NC)"

.PHONY: docker-compose-down
docker-compose-down: ## Stop and remove containers
	@echo "$(YELLOW)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

.PHONY: docker-compose-logs
docker-compose-logs: ## Show docker-compose logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: docker-compose-ps
docker-compose-ps: ## Show running services
	$(DOCKER_COMPOSE) ps

# =============================================================================
# AWS ECR
# =============================================================================

.PHONY: ecr-login
ecr-login: ## Login to AWS ECR (requires AWS CLI)
	@echo "$(BLUE)Logging in to AWS ECR...$(NC)"
	@if [ -z "$(shell echo $(IMG) | grep -o 'dkr.ecr')" ]; then \
		echo "$(RED)✗ IMG does not appear to be an ECR repository$(NC)"; \
		echo "$(YELLOW)Expected format: <account>.dkr.ecr.<region>.amazonaws.com/<repo>:tag$(NC)"; \
		exit 1; \
	fi
	$(eval ACCOUNT := $(shell echo $(IMG) | cut -d. -f1))
	$(eval ECR_REGION := $(shell echo $(IMG) | cut -d. -f4))
	@echo "$(YELLOW)Account: $(ACCOUNT)$(NC)"
	@echo "$(YELLOW)Region: $(ECR_REGION)$(NC)"
	aws ecr get-login-password --region $(ECR_REGION) | \
		$(DOCKER) login --username AWS --password-stdin $(ACCOUNT).dkr.ecr.$(ECR_REGION).amazonaws.com
	@echo "$(GREEN)✓ Logged in to ECR$(NC)"

.PHONY: docker-push
docker-push: ecr-login ## Push Docker image to ECR
	@echo "$(BLUE)Pushing image to ECR: $(IMG)$(NC)"
	$(DOCKER) push $(IMG)
	@echo "$(GREEN)✓ Image pushed: $(IMG)$(NC)"

.PHONY: docker-pull
docker-pull: ecr-login ## Pull Docker image from ECR
	@echo "$(BLUE)Pulling image from ECR: $(IMG)$(NC)"
	$(DOCKER) pull $(IMG)
	@echo "$(GREEN)✓ Image pulled: $(IMG)$(NC)"

# =============================================================================
# Testing & Validation
# =============================================================================

.PHONY: test
test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTHON) -m pytest tests/ -v

.PHONY: test-venv
test-venv: ## Run tests in virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(RED)✗ Virtual environment not found. Run 'make venv' first.$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Running tests in virtual environment...$(NC)"
	$(PYTHON_VENV) -m pytest tests/ -v

.PHONY: validate
validate: ## Run all validation scripts
	@echo "$(BLUE)Running validation scripts...$(NC)"
	$(PYTHON) validate_step1.py
	$(PYTHON) validate_step2.py
	$(PYTHON) validate_step3.py
	$(PYTHON) validate_step4.py
	$(PYTHON) validate_step5.py
	$(PYTHON) validate_step6.py
	$(PYTHON) validate_step7.py
	@echo "$(GREEN)✓ All validations complete$(NC)"

.PHONY: lint
lint: ## Run linting checks
	@echo "$(BLUE)Running linting checks...$(NC)"
	$(PYTHON) -m flake8 src/ --max-line-length=120 || true
	@echo "$(GREEN)✓ Linting complete$(NC)"

# =============================================================================
# Cleanup
# =============================================================================

.PHONY: clean
clean: ## Clean build artifacts and caches
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ .coverage htmlcov/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

.PHONY: clean-all
clean-all: clean clean-venv docker-compose-down ## Clean everything
	@echo "$(YELLOW)Removing Docker images...$(NC)"
	$(DOCKER) rmi $(IMG) 2>/dev/null || true
	@echo "$(GREEN)✓ Full cleanup complete$(NC)"

# =============================================================================
# Health Checks
# =============================================================================

.PHONY: health
health: ## Check health endpoint
	@echo "$(BLUE)Checking health endpoint...$(NC)"
	curl -f http://localhost:$(HTTP_PORT)/healthz && echo "" || echo "$(RED)✗ Health check failed$(NC)"

.PHONY: metrics
metrics: ## Check metrics endpoint
	@echo "$(BLUE)Fetching metrics...$(NC)"
	curl -s http://localhost:$(HTTP_PORT)/metrics | head -30

# =============================================================================
# Info
# =============================================================================

.PHONY: info
info: ## Show configuration info
	@echo "$(BLUE)kvs-infer Configuration$(NC)"
	@echo "$(YELLOW)Python:$(NC)        $(shell $(PYTHON) --version)"
	@echo "$(YELLOW)Docker:$(NC)        $(shell $(DOCKER) --version)"
	@echo "$(YELLOW)IMG:$(NC)           $(IMG)"
	@echo "$(YELLOW)CONFIG:$(NC)        $(CONFIG)"
	@echo "$(YELLOW)GPU:$(NC)           $(GPU)"
	@echo "$(YELLOW)HTTP_PORT:$(NC)     $(HTTP_PORT)"
	@echo "$(YELLOW)AWS_REGION:$(NC)    $(REGION)"
	@echo "$(YELLOW)CUDA Available:$(NC) $(shell $(PYTHON) -c 'import torch; print(torch.cuda.is_available())' 2>/dev/null || echo 'N/A')"

.PHONY: version
version: ## Show version
	@echo "kvs-infer v1.0"
