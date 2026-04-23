# MM-Wiki CLI Skill

Use this skill when you need to operate MM-Wiki from Codex via the local `mmwiki` CLI.

## Commands

- Login: `./mmwiki --server http://127.0.0.1:8080 --profile dev auth login --username admin --password '***'`
- Status: `./mmwiki --profile dev auth status`
- Add document: `./mmwiki --profile dev doc add --name "Doc" --space-name "研发" --parent-id 100 --from-md ./doc.md`
- Pull document: `./mmwiki --profile dev doc pull --document-id 123 --md ./docs/123.md`
- Push document: `./mmwiki --profile dev doc push --document-id 123 --md ./docs/123.md`
- Title search: `./mmwiki --profile dev search title 关键字`
- Content search: `./mmwiki --profile dev search content 关键字`
- User info: `./mmwiki --profile dev user info`
- User follows: `./mmwiki --profile dev user follows`
- User activity: `./mmwiki --profile dev user activity`

## Notes

- First use `--server` once to bind it into the profile.
- `search content` uses local SQLite FTS built from pulled/pushed docs.
- `doc push` blocks remote drift unless `--force`.
