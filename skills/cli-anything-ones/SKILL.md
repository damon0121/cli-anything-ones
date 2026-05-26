---
name: cli-anything-ones
description: Use when reading ONES bug or issue URLs from any project through the `cli-anything-ones` read-only CLI.
---

# cli-anything-ones

Use `cli-anything-ones` to parse ONES issue URLs, read issue details, and download attachments.

## Required Configuration

An ONES access token must be configured for commands that call ONES APIs. Prefer an existing `ONES_ACCESS_TOKEN` environment variable; otherwise use `cli-anything-ones config set-token`.

## Commands

```bash
cli-anything-ones issue parse "<ONES issue URL>" --json
cli-anything-ones issue list "<ONES project or issue URL>" --json
cli-anything-ones issue list "<ONES project or issue URL>" --exclude-status 关闭 --json
cli-anything-ones issue list "<ONES project or issue URL>" --mine --exclude-status 关闭 --json
cli-anything-ones issue list "<ONES project or issue URL>" --assignee-id <user-id> --json
cli-anything-ones issue get "<ONES issue URL>" --json
cli-anything-ones issue get "<ONES issue URL>" --format markdown
cli-anything-ones attachment download "<ONES issue URL>" --output-dir /tmp/ones --json
cli-anything-ones config set-token
cli-anything-ones doctor --json
```

## Agent Guidance

- Prefer `--json` for programmatic use.
- Use `issue list` when the task asks for work items in a project or team.
- Use repeated `--exclude-status <name-or-id>` values to omit closed or otherwise unwanted statuses.
- Use `--mine` to filter by the current OpenAPI token user, or `--assignee-id <user-id>` when a specific assignee is known.
- Do not request attachment URLs unless needed.
- Use `attachment download` when screenshots or files are necessary to diagnose a bug.
- This CLI is read-only and does not comment on or mutate ONES issues.
