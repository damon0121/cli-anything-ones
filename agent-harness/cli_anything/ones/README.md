# cli-anything-ones

Read-only ONES issue CLI for coding agents.

## Install

```bash
uv tool install -e ./agent-harness --python python3.11 --force
```

## Environment

An ONES access token is required for commands that call ONES APIs. You can export it for the current shell or save it to the local CLI config file:

```bash
export ONES_ACCESS_TOKEN=...
cli-anything-ones config set-token
```

The environment variable takes precedence over the saved token.

Optional:

```bash
export ONES_BASE_URL=https://sz.ones.cn
export ONES_TEAM_ID=HbudLR1b
```

## Usage

```bash
cli-anything-ones issue parse "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --json
cli-anything-ones issue get "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218"
cli-anything-ones issue get "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --json
cli-anything-ones attachment download "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/issue/JHWX-10218" --output-dir /tmp/ones
cli-anything-ones config set-token
cli-anything-ones doctor --json
```

## Safety

- This CLI does not write to ONES.
- The token is read from `ONES_ACCESS_TOKEN` or the local CLI config file.
- Tokens are never accepted as command-line arguments or printed by `doctor`.
- Attachment URLs are hidden by default. Use `--include-attachment-urls` only when needed.
