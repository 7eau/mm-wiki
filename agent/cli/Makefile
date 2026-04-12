# MM-Wiki CLI Makefile

.PHONY: build clean install test help

# Variables
BINARY_NAME=mmwiki-cli
VERSION=$(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS=-ldflags "-X main.version=${VERSION}"
GO=go

# Default target
all: build

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build the CLI binary
	@echo "Building $(BINARY_NAME) version $(VERSION)..."
	$(GO) mod tidy
	$(GO) build $(LDFLAGS) -o $(BINARY_NAME) ./
	@echo "Build complete: $(BINARY_NAME)"

clean: ## Clean build artifacts
	@echo "Cleaning..."
	rm -f $(BINARY_NAME)
	$(GO) clean
	@echo "Clean complete"

install: build ## Install binary to /usr/local/bin
	@echo "Installing $(BINARY_NAME) to /usr/local/bin..."
	cp $(BINARY_NAME) /usr/local/bin/
	chmod +x /usr/local/bin/$(BINARY_NAME)
	@echo "Install complete"

uninstall: ## Uninstall binary from /usr/local/bin
	@echo "Uninstalling $(BINARY_NAME)..."
	rm -f /usr/local/bin/$(BINARY_NAME)
	@echo "Uninstall complete"

test: ## Run tests
	@echo "Running tests..."
	$(GO) test -v ./...

# Cross compilation
build-all: ## Build for multiple platforms
	@echo "Building for multiple platforms..."
	# Linux
	GOOS=linux GOARCH=amd64 $(GO) build $(LDFLAGS) -o $(BINARY_NAME)-linux-amd64 ./
	GOOS=linux GOARCH=arm64 $(GO) build $(LDFLAGS) -o $(BINARY_NAME)-linux-arm64 ./
	# macOS
	GOOS=darwin GOARCH=amd64 $(GO) build $(LDFLAGS) -o $(BINARY_NAME)-darwin-amd64 ./
	GOOS=darwin GOARCH=arm64 $(GO) build $(LDFLAGS) -o $(BINARY_NAME)-darwin-arm64 ./
	# Windows
	GOOS=windows GOARCH=amd64 $(GO) build $(LDFLAGS) -o $(BINARY_NAME)-windows-amd64.exe ./
	@echo "Cross-platform builds complete"

# Development targets
run: build ## Build and run (for development)
	./$(BINARY_NAME) --help

dev-login: build ## Quick login for development
	./$(BINARY_NAME) login --url http://localhost:8081 --username admin --password admin

fmt: ## Format Go code
	$(GO) fmt ./...

vet: ## Run go vet
	$(GO) vet ./...

lint: ## Run linter (requires golangci-lint)
	golangci-lint run ./...
