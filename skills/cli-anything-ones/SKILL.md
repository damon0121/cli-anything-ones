---
name: cli-anything-ones
description: Use when reading ONES bug or issue URLs from any project through the `cli-anything-ones` read-only CLI.
---

# cli-anything-ones

Use `cli-anything-ones` to parse ONES issue URLs, read issue details, and download attachments.

## Required Environment

`ONES_ACCESS_TOKEN` must be set for commands that call ONES APIs.

## Commands

```bash
cli-anything-ones issue parse "<ONES issue URL>" --json
cli-anything-ones issue get "<ONES issue URL>" --json
cli-anything-ones issue get "<ONES issue URL>" --format markdown
cli-anything-ones attachment download "<ONES issue URL>" --output-dir /tmp/ones --json
cli-anything-ones doctor --json
```

## Agent Guidance

- Prefer `--json` for programmatic use.
- Do not request attachment URLs unless needed.
- Use `attachment download` when screenshots or files are necessary to diagnose a bug.
- This CLI is read-only and does not comment on or mutate ONES issues.
