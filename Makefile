# Video Downloader API Makefile

.PHONY: help install run-dev run-prod test clean docker-build docker-run docker-stop docker-clean setup-dirs

# Variables
PYTHON := python3
PIP := pip
DOCKER := docker
APP_NAME := video-downloader
CONTAINER_NAME := video-downloader-app
PORT := 8888

help:
	@echo "Video Downloader API Makefile commands:"
	@echo "make install        - Install dependencies"
	@echo "make run-dev       - Run development server"
	@echo "make run-prod      - Run production server"
	@echo "make test          - Run tests"
	@echo "make clean         - Clean up cache and temporary files"
	@echo "make docker-build  - Build Docker image"
	@echo "make docker-run    - Run Docker container"
	@echo "make docker-stop   - Stop Docker container"
	@echo "make docker-clean  - Clean Docker resources"
	@echo "make setup-dirs    - Create required directories"

install:
	$(PIP) install -r requirements.txt

run-dev:
	$(PYTHON) scripts/run_dev.py

run-prod:
	$(PYTHON) scripts/run_prod.py

test:
	pytest tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

docker-build:
	$(DOCKER) build -t $(APP_NAME) .

docker-run:
	$(DOCKER) run -d \
		-p $(PORT):$(PORT) \
		-v $(PWD)/downloaded_videos:/app/downloaded_videos \
		-v $(PWD)/logs:/app/logs \
		--name $(CONTAINER_NAME) \
		$(APP_NAME)

docker-stop:
	$(DOCKER) stop $(CONTAINER_NAME) || true
	$(DOCKER) rm $(CONTAINER_NAME) || true

docker-clean:
	make docker-stop
	$(DOCKER) rmi $(APP_NAME) || true

setup-dirs:
	mkdir -p downloaded_videos/downloads downloaded_videos/fresh_downloads logs static cookies
	chmod -R 755 downloaded_videos logs static cookies


