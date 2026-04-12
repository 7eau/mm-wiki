# MM-Wiki CLI Examples

This directory contains example scripts and use cases for the MM-Wiki CLI tool.

## Prerequisites

1. Build the CLI tool:
```bash
cd agent/cli
go mod tidy
go build -o mmwiki-cli ./
```

2. Ensure your MM-Wiki server is running and accessible

## Examples

### 1. Basic Setup (`setup.sh`)

Demonstrates login, space creation, and basic document structure setup.

```bash
./agent/examples/setup.sh http://localhost:8081 admin password
```

### 2. Bulk Import (`import.sh`)

Shows how to bulk import documents from a directory structure.

```bash
./agent/examples/import.sh http://localhost:8081 admin password ./docs
```

### 3. Backup Export (`backup.sh`)

Exports all documents from a space to local files.

```bash
./agent/examples/backup.sh http://localhost:8081 admin password 1 ./backup
```

### 4. User Management (`manage-users.sh`)

Bulk user creation and management example.

```bash
./agent/examples/manage-users.sh http://localhost:8081 admin password users.csv
```

## Sample CSV Format for User Import

```csv
username,name,email,role
john,John Doe,john@example.com,3
jane,Jane Smith,jane@example.com,3
bob,Bob Admin,bob@example.com,2
```
