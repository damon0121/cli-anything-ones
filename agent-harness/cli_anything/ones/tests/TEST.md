# Test Plan

## Unit Tests

- URL parsing for ONES hash URLs.
- Project URL parsing for list commands without requiring an issue key.
- Issue-list pagination and summary normalization.
- Issue-list projectID fallback and client-side sprint filtering.
- Issue-list status exclusion by status name or ID while continuing pagination.
- Issue-list assignee filtering while continuing pagination.
- Issue-list limit validation.
- Current OpenAPI token user resolution via `/oauth2/introspect`.
- Trusted host checks for ONES SaaS hosts.
- Untrusted issue URL rejection before network discovery.
- Attachment URL host validation and filename sanitization.
- Attachment redirect target validation.
- Saved token configuration and precedence.
- Markdown-safe formatting helpers.

## E2E Tests

- CLI help can be executed as a subprocess.
- `issue parse --json` can be executed as a subprocess without `ONES_ACCESS_TOKEN`.
- `issue list --help` can be executed as a subprocess without `ONES_ACCESS_TOKEN`.
- `config set-token --stdin` saves a local token that `doctor --json` can detect.

Live ONES API tests require a real `ONES_ACCESS_TOKEN` and are intentionally not part of the default test suite to avoid leaking credentials in CI logs.

## Test Results

Command:

```bash
uv run --python python3.11 --with pytest --with click python -m pytest cli_anything/ones/tests -v
```

Result:

```text
27 passed in 0.70s
```

## Live Smoke Results

- `cli-anything-ones issue parse <JHWX-10218 URL> --json` resolved `baseURL` to `https://sz.ones.cn`.
- `cli-anything-ones issue get <JHWX-10218 URL> --format markdown` read the issue title, fields, and attachment metadata.
- `cli-anything-ones attachment download <JHWX-10218 URL> --output-dir <tmp> --json` downloaded `image.png` successfully.
- `cli-anything-ones issue parse <untrusted URL> --json` rejected the URL before ONES discovery.
