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
./mmwiki --profile dev space tree --space-id 10
./mmwiki --profile dev space valid-list
./mmwiki --profile dev index export --out ./artifacts/content.db
./mmwiki --profile dev index install --from ./artifacts/content.db
./mmwiki --profile dev index preindex-follows-if-missing
./mmwiki-preindex --profile dev --document-ids 100,101 --workers 4
./mmwiki-preindex --profile dev --space-ids 10,11
./mmwiki-preindex --profile dev --doc-range-start 200 --doc-range-end 220
```

## Cross-platform install script

From repo root, run:

```bash
python scripts/install_mmwiki.py
```

This installs launchers into the current terminal path (`$PWD`) by default.
For example, from repo root it creates:

- `./mmwiki`
- `./mmwiki-preindex`

Optional custom target:

```bash
python scripts/install_mmwiki.py --bin-dir /custom/bin
```

When installed in the current directory, run directly:

```bash
./mmwiki --help
```

For global PATH usage, install to a custom bin dir (for example `~/.local/bin`) with `--bin-dir`.

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
- `mmwiki index preindex-follows-if-missing` (skip when local `content.db` already exists)

Use standalone preindexing when bootstrapping from explicit IDs, spaces, or ranges:

- `mmwiki-preindex --document-ids 100,101`
- `mmwiki-preindex --space-ids 10,11`
- `mmwiki-preindex --doc-range-start 200 --doc-range-end 260`

Space discovery commands:

- `mmwiki space tree --space-id <id>`
- `mmwiki space valid-list [--max-pages <n>]`

Structured space tree output fields:

- `space_id`
- `root_document_id`
- `documents` (ordered `{document_id, title}`)
- `document_count`
- `errors`

Structured valid space list output fields:

- `spaces` (each item: `space_id`, `space_name`, `root_document_id`)
- `valid_count`
- `invalid_count`
- `errors`

Structured preindex output fields:

- `requested_count`
- `resolved_count`
- `indexed_count`
- `skipped_count`
- `failed_count`
- `errors`
- `skipped_reason` (when skipped)

## MCP server

```bash
pip install mcp
python -m agent.mmwiki.mcp_server
```

Environment:

- `MMWIKI_MCP_TRANSPORT` (default `stdio`)

MCP tools:

- `space_tree(space_id, profile="default", server=None)`
- `space_valid_list(profile="default", server=None)`
