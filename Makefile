.PHONY: help install dev backend-dev frontend-dev docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  install      Install all dependencies (backend & frontend)"
	@echo "  dev          Run both backend and frontend in development mode"
	@echo "  backend-dev  Run only the backend development server"
	@echo "  frontend-dev Run only the frontend development server"
	@echo "  docker-up    Start the backend infrastructure via Docker"
	@echo "  docker-down  Stop the Docker containers"

install:
	@echo "Installing backend dependencies..."
	cd backend && make install
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev:
	@echo "Starting backend and frontend..."
	@make -j 2 backend-dev frontend-dev

backend-dev:
	cd backend && make dev

frontend-dev:
	cd frontend && npm run dev

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
