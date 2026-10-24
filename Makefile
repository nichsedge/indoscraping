.PHONY: all build-go test test-py test-go check-browser clean help

all: build-go test

help:
	@echo "Indoscraping Build & Test Commands:"
	@echo "  make build-go     - Compile native Go binary (bin/indoscraping)"
	@echo "  make test         - Run both Python (pytest) and Go (go test) suites"
	@echo "  make test-py      - Run Python pytest suite"
	@echo "  make test-go      - Run Go test suite"
	@echo "  make check-browser- Verify system Chromium/Chrome detection"
	@echo "  make clean        - Remove caches and build artifacts"

build-go:
	go build -o bin/indoscraping ./cmd/indoscraping

test: test-py test-go

test-py:
	uv run pytest

test-go:
	go test ./...

check-browser:
	uv run indoscraping check-browser

clean:
	rm -rf .pytest_cache build dist *.egg-info *.log
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
