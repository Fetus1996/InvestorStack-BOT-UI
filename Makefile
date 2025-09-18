.PHONY: install run test clean dev setup

# Install dependencies
install:
	pip install -r backend/requirements.txt

# Set up environment
setup:
	cp .env.example .env
	cp config.example.json config.json
	@echo "Setup complete. Please edit .env with your API credentials."

# Run the application
run:
	uvicorn backend.app:app --reload --host 0.0.0.0 --port 9000

# Run in development mode
dev:
	uvicorn backend.app:app --reload --host 0.0.0.0 --port 9000 --log-level debug

# Run tests
test:
	cd backend && python -m pytest tests/ -v

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f grid.db
	rm -f .coverage

# Run specific test file
test-grid:
	cd backend && python -m pytest tests/test_grid_calculator.py -v

test-config:
	cd backend && python -m pytest tests/test_config_validation.py -v

test-flow:
	cd backend && python -m pytest tests/test_start_stop.py -v

# Database operations
db-reset:
	rm -f grid.db
	@echo "Database reset complete."

# Help
help:
	@echo "Available commands:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make setup      - Set up environment files"
	@echo "  make run        - Run the application"
	@echo "  make dev        - Run in development mode with debug logging"
	@echo "  make test       - Run all tests"
	@echo "  make clean      - Clean up cache files"
	@echo "  make db-reset   - Reset the database"