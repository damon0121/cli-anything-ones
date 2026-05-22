---
name: cli-anything-ones
description: Use when reading ONES bug or issue URLs from any project through the `cli-anything-ones` read-only CLI.
---

# cli-anything-ones

Use `cli-anything-ones` to parse ONES issue URLs, read issue details, and download attachments.

## Required Configuration

An ONES access token must be configured for commands that call ONES APIs. Prefer an existing `ONES_ACCESS_TOKEN` environment variable; otherwise use `cli-anything-ones config set-token`.

Optional environment variables:

- `ONES_BASE_URL` for self-hosted ONES domains or explicit region selection.
- `ONES_TEAM_ID` when a URL does not contain a team ID.

## Commands

```bash
cli-anything-ones issue parse "<ONES issue URL>" --json
cli-anything-ones issue get "<ONES issue URL>" --json
cli-anything-ones issue get "<ONES issue URL>" --format markdown
cli-anything-ones attachment download "<ONES issue URL>" --output-dir /tmp/ones --json
cli-anything-ones config set-token
cli-anything-ones doctor --json
```

## Agent Guidance

- Prefer `--json` for programmatic use.
- Do not request attachment URLs unless needed.
- Use `attachment download` when screenshots or files are necessary to diagnose a bug.
- This CLI is read-only and does not comment on or mutate ONES issues.
