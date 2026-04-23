# MM-Wiki CLI Skill

Use this skill when you need to operate MM-Wiki from Codex via the local `mmwiki` CLI.

## Commands

- Login: `./mmwiki --server http://127.0.0.1:8080 --profile dev auth login --username admin --password '***'`
- Status: `./mmwiki --profile dev auth status`
- Add document: `./mmwiki --profile dev doc add --name "Doc" --space-name "研发" --parent-id 100 --from-md ./doc.md`
- Pull document: `./mmwiki --profile dev doc pull --document-id 123 --md ./docs/123.md`
- Push document: `./mmwiki --profile dev doc push --document-id 123 --md ./docs/123.md`
- Delete local markdown (retain index): `./mmwiki --profile dev doc delete-local --md ./docs/123.md --document-id 123`
- Title search: `./mmwiki --profile dev search title 关键字`
- Content search: `./mmwiki --profile dev search content 关键字`
- Analyze summary: `./mmwiki --profile dev analyze summary --document-ids 123,456 --max-sentences 3`
- Analyze keywords: `./mmwiki --profile dev analyze keywords --document-ids 123,456 --top-k 8`
- Export index DB: `./mmwiki --profile dev index export --out ./artifacts/content.db`
- Install index DB: `./mmwiki --profile dev index install --from ./artifacts/content.db --backup ./artifacts/content.backup.db`
- Follow bootstrap preindex (if local index missing): `./mmwiki --profile dev index preindex-follows-if-missing`
- Standalone preindex by docs/spaces/range: `./mmwiki-preindex --profile dev --document-ids 123,456 --space-ids 10 --doc-range-start 200 --doc-range-end 220 --workers 4`
- User info: `./mmwiki --profile dev user info`
- User follows: `./mmwiki --profile dev user follows`
- User activity: `./mmwiki --profile dev user activity`

## Notes

- First use `--server` once to bind it into the profile.
- `search content` uses local SQLite FTS built from pulled/pushed docs.
- `doc delete-local` removes local markdown + snapshots but keeps index rows for fast retrieval.
- `doc push` blocks remote drift unless `--force`.
- `index install` atomically replaces local `content.db`, and backs up existing DB (auto path if not provided).
- `preindex-follows-if-missing` exits early with `skipped_reason=index_exists` when local `content.db` already exists.
