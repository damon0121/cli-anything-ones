# cli-anything-ones

Read-only ONES issue CLI for coding agents.

## Install

```bash
uv tool install -e ./agent-harness --python python3.11 --force
```

## Environment

```bash
export ONES_ACCESS_TOKEN=...
```

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
cli-anything-ones doctor --json
```

## Safety

- This CLI does not write to ONES.
- The token is only read from `ONES_ACCESS_TOKEN`.
- Attachment URLs are hidden by default. Use `--include-attachment-urls` only when needed.
