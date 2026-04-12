# MM-Wiki Agent Tools

This directory contains tools and skills for AI agents to interact with MM-Wiki.

## Directory Structure

```
agent/
├── cli/              # Command-line interface tool
│   ├── client/       # HTTP API client library
│   ├── cmd/          # CLI command implementations
│   ├── main.go       # Entry point
│   ├── go.mod        # Go module definition
│   └── Makefile      # Build automation
├── skills/           # Skill documentation for AI agents
│   └── SKILL.md      # Comprehensive usage guide
└── examples/         # Example scripts
    ├── setup.sh      # Basic setup example
    ├── backup.sh     # Backup export script
    └── README.md     # Examples documentation
```

## Quick Start

### 1. Build the CLI Tool

```bash
cd agent/cli
make build

# Or use go directly
go mod tidy
go build -o mmwiki-cli ./
```

### 2. Login to Your MM-Wiki Server

```bash
./mmwiki-cli login --url http://wiki.example.com:8081 --username admin --password yourpassword
```

### 3. Start Using

```bash
# List users
./mmwiki-cli user list

# Create a space
./mmwiki-cli space create --name "My Project" --description "Documentation" --owner 1

# List documents
./mmwiki-cli doc list --space 1

# Read a document
./mmwiki-cli doc read --id 1
```

## CLI Features

- **User Management**: List, create, update, delete users
- **Space Management**: Manage wiki spaces
- **Document Management**: CRUD operations on documents
- **Tree View**: Visualize document hierarchy
- **Content Operations**: Read/write document content via files or stdin

## Authentication

The CLI uses session-based authentication:
- Session is saved to `~/.mmwiki-cli` after login
- Session persists for 24 hours
- No need to provide credentials for subsequent commands

## For AI Agents

See [skills/SKILL.md](skills/SKILL.md) for comprehensive documentation on:
- Available commands and options
- API endpoint mappings
- Error handling
- Best practices for automation

## Examples

See [examples/](examples/) directory for practical scripts:
- `setup.sh` - Initialize a wiki with structure
- `backup.sh` - Export all documents

## Architecture

```
┌─────────────────┐     HTTP/HTTPS      ┌─────────────────┐
│   mmwiki-cli    │ ◄────────────────►  │   MM-Wiki       │
│   (CLI Tool)    │    Session Cookie   │   Server        │
└─────────────────┘                     └─────────────────┘
        │
        │ Reads/Writes
        ▼
┌─────────────────┐
│ ~/.mmwiki-cli   │
│ (Session Cache) │
└─────────────────┘
```

## Development

### Building

```bash
cd agent/cli
make build
```

### Cross-compilation

```bash
make build-all
```

### Testing

```bash
make test
```

## License

Same as MM-Wiki (MIT License)
