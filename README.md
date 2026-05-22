# cli-anything-ones

Read-only CLI-Anything harness for reading ONES issues and attachments from coding agents.

## What It Does

- Parses ONES issue URLs.
- Reads issue details, comments, custom fields, and attachments.
- Downloads issue attachments when needed for diagnosis.
- Exposes an agent skill under `skills/cli-anything-ones`.
- Never writes comments, status, fields, or other data back to ONES.

## Repository Layout

```text
agent-harness/                  Python package and CLI implementation
agent-harness/ONES.md           Harness behavior and safety notes
agent-harness/cli_anything/ones Python source, tests, and package README
skills/cli-anything-ones        OpenCode skill for using the CLI
```

## Install

From the repository root:

```bash
uv tool install -e ./agent-harness --python python3.11 --force
```

The command installs the `cli-anything-ones` executable.

## Environment

`ONES_ACCESS_TOKEN` is required for commands that call ONES APIs:

```bash
export ONES_ACCESS_TOKEN=...
```

Optional settings:

```bash
export ONES_BASE_URL=https://sz.ones.cn
export ONES_TEAM_ID=HbudLR1b
```

`ONES_TEAM_ID` is optional when the issue URL already contains a team ID.

## Usage

```bash
cli-anything-ones issue parse "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --json
cli-anything-ones issue get "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218"
cli-anything-ones issue get "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --json
cli-anything-ones attachment download "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --output-dir /tmp/ones --json
cli-anything-ones doctor --json
```

For programmatic agent use, prefer `--json`.

## Safety

- This CLI is read-only.
- Tokens are read only from `ONES_ACCESS_TOKEN`.
- Tokens are never accepted as command-line arguments or printed by `doctor`.
- Temporary attachment URLs are hidden by default. Use `--include-attachment-urls` only when needed.
- Attachment downloads are restricted to ONES hosts unless `--allow-external-attachment-hosts` is explicitly provided.

## Development

Run tests from the package directory:

```bash
cd agent-harness
python -m pytest cli_anything/ones/tests
```

## License

No license has been declared yet.
