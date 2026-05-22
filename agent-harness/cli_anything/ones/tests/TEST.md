# Test Plan

## Unit Tests

- URL parsing for ONES hash URLs.
- Trusted host checks for ONES SaaS hosts.
- Untrusted issue URL rejection before network discovery.
- Attachment URL host validation and filename sanitization.
- Attachment redirect target validation.
- Markdown-safe formatting helpers.

## E2E Tests

- CLI help can be executed as a subprocess.
- `issue parse --json` can be executed as a subprocess without `ONES_ACCESS_TOKEN`.

Live ONES API tests require a real `ONES_ACCESS_TOKEN` and are intentionally not part of the default test suite to avoid leaking credentials in CI logs.

## Test Results

Command:

```bash
uv run --python python3.11 --with pytest --with click python -m pytest cli_anything/ones/tests -v
```

Result:

```text
11 passed in 0.45s
```

## Live Smoke Results

- `cli-anything-ones issue parse <JHWX-10218 URL> --json` resolved `baseURL` to `https://sz.ones.cn`.
- `cli-anything-ones issue get <JHWX-10218 URL> --format markdown` read the issue title, fields, and attachment metadata.
- `cli-anything-ones attachment download <JHWX-10218 URL> --output-dir <tmp> --json` downloaded `image.png` successfully.
- `cli-anything-ones issue parse <untrusted URL> --json` rejected the URL before ONES discovery.
