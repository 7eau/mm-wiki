# Repository Guidelines

## Project Structure & Module Organization
- `main.go` and `router.go` are the application entrypoints.
- `app/` contains core backend code:
  - `controllers/` for HTTP handlers
  - `models/` for data access/domain models
  - `services/` and `modules/` for business logic
  - `utils/` for shared helpers
- `install/` contains the installer app (`install` binary and installer controllers/storage).
- `views/` stores server-rendered templates; `static/` stores CSS/JS/images/plugins.
- `conf/` holds runtime config templates; `docs/` includes SQL and operational docs.
- Build/package scripts live in `build.sh`, `pack.sh`, and `scripts/run.sh`.

## Build, Test, and Development Commands
- `go build ./` — compile the main `mm-wiki` binary locally.
- `go test ./...` — run all Go tests (mostly utility-layer tests).
- `./build.sh` — produce a local release layout under `release/`.
- `./pack.sh linux amd64` — build and archive a target package (see `./pack.sh help`).
- `./mm-wiki --conf conf/mm-wiki.conf` — run with explicit config after install/setup.

## Coding Style & Naming Conventions
- Use standard Go formatting: run `gofmt` on changed Go files before submitting.
- Keep package names short/lowercase; exported identifiers in `CamelCase`, unexported in `camelCase`.
- Match existing layering: controllers should orchestrate, services/modules hold business rules, models handle persistence.
- Keep template and static asset names descriptive and feature-scoped (example: `views/space/...`, `static/js/...`).

## Testing Guidelines
- Use Go’s `testing` package; place tests next to code as `*_test.go`.
- Prefer table-driven tests for utility/service behavior.
- Run `go test ./...` before opening a PR; add/adjust tests for any logic change.

## Commit & Pull Request Guidelines
- Follow existing commit style with clear prefixes, e.g. `fix: ...`, `feat: ...`, `[feat] ...`.
- Keep commits focused (one logical change per commit) and reference issue IDs when applicable.
- PRs should include: purpose, key changes, test evidence (`go test ./...` output), and screenshots for UI/template updates.
- Link related issues and note config/migration impacts (especially `conf/` and `docs/databases/` updates).

## Security & Configuration Tips
- Never commit real secrets; keep credentials in runtime config files derived from `conf/template.conf`.
- Validate DB-related changes against `docs/databases/` scripts and document any required migration steps.
