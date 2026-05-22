# ONES CLI Harness

This harness exposes a read-only, agent-friendly CLI for ONES work items.

## Backend

- ONES OpenAPI v2 over HTTPS.
- Authentication uses `ONES_ACCESS_TOKEN` from the environment first, then the local CLI config file.
- `ONES_BASE_URL` is optional for self-hosted ONES domains.
- `ONES_TEAM_ID` is optional when the issue URL already contains a team ID.

## Commands

- `cli-anything-ones issue parse <url>` parses an ONES issue URL.
- `cli-anything-ones issue get <url>` reads issue detail, comments, attachments, and field metadata.
- `cli-anything-ones attachment download <url> --output-dir <dir>` downloads issue attachments.
- `cli-anything-ones config set-token` saves the ONES access token to the local CLI config file.
- `cli-anything-ones doctor` checks local configuration without printing secrets.

## Safety

- The harness never writes comments, status, fields, or other ONES data.
- Temporary attachment URLs are not printed unless explicitly requested.
- Tokens are never accepted as command-line arguments and are never logged.
- The saved token is written with `0600` file permissions.
- By default, tokens are only sent to `ones.cn`, `*.ones.cn`, and `*.myones.net` hosts. Set `ONES_BASE_URL` explicitly for self-hosted ONES domains.

## Verified Behavior

The implementation was derived from a working Node prototype that successfully read `JHWX-10218` and resolved the ONES SaaS region URL from `https://ones.cn` to `https://sz.ones.cn`.
