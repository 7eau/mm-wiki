# mmwiki CLI

Python local CLI for MM-Wiki with shared core used by CLI and MCP server.

## CLI

Use executable at repo root:

```bash
./mmwiki --server http://127.0.0.1:8080 --profile dev auth login --username admin --password xxx
./mmwiki --profile dev doc pull --document-id 100 --md ./docs/100.md
./mmwiki --profile dev doc push --document-id 100 --md ./docs/100.md
./mmwiki --profile dev doc delete-local --md ./docs/100.md --document-id 100
./mmwiki --profile dev search content keyword
./mmwiki --profile dev index export --out ./artifacts/content.db
./mmwiki --profile dev index install --from ./artifacts/content.db
```

## Cross-platform install script

From repo root, run:

```bash
python scripts/install_mmwiki.py
```

Optional custom target:

```bash
python scripts/install_mmwiki.py --bin-dir /custom/bin
```

Defaults:

- Windows: `%LOCALAPPDATA%\Programs\mmwiki\bin`
- macOS/Linux: `~/.local/bin`

After install, add that directory to your `PATH`, reopen terminal, then run:

```bash
mmwiki --help
```

Uninstall launcher:

```bash
python scripts/uninstall_mmwiki.py
```

Uninstall launcher + local state:

```bash
python scripts/uninstall_mmwiki.py --purge-state
```

Global flags:

- `--server`
- `--profile`
- `--json`

## Local state

- Profiles: `${XDG_CONFIG_HOME:-~/.config}/mmwiki/profiles.json`
- Cookies: `${XDG_DATA_HOME:-~/.local/share}/mmwiki/cookies/*.cookies.txt`
- Drift snapshots: `${XDG_DATA_HOME:-~/.local/share}/mmwiki/cache/snapshots.json`
- Search index: `${XDG_DATA_HOME:-~/.local/share}/mmwiki/index/content.db`

`doc delete-local` removes local markdown + matching drift snapshots, and keeps index rows for fast local `search content` / `analyze` retrieval.

Use index portability commands to move local index metadata between machines:

- `mmwiki index export --out <file>`
- `mmwiki index install --from <file> [--backup <file>]`

## MCP server

```bash
pip install mcp
python -m agent.mmwiki.mcp_server
```

Environment:

- `MMWIKI_MCP_TRANSPORT` (default `stdio`)
