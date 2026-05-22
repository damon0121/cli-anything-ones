import json
import sys
from urllib.parse import urlparse

import click

from . import __version__
from .core.api import OnesClient
from .core.attachments import download_attachments
from .core.config import doctor_payload, resolve_config
from .core.errors import ApiError, UsageError
from .core.formatting import print_payload
from .core.issues import DEFAULT_MAX_PAGES, fetch_issue, validate_max_pages
from .core.parse import parse_ones_issue_url


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="cli-anything-ones")
def cli():
    """Read-only CLI-Anything harness for ONES issues."""


@cli.group()
def issue():
    """Parse and read ONES issues."""


@issue.command("parse")
@click.argument("url")
@click.option("--json", "json_output", is_flag=True, help="Output JSON.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    show_default=True,
)
def issue_parse(url, json_output, output_format):
    """Parse an ONES issue URL without requiring a token."""
    output_format = _resolve_output_format(json_output, output_format)
    parsed = parse_ones_issue_url(url)
    config = resolve_config(parsed, require_token=False)
    payload = {**parsed.to_dict(), "baseURL": config.base_url, "teamID": config.team_id}
    click.echo(print_payload(payload, output_format), nl=False)


@issue.command("get")
@click.argument("url")
@click.option("--json", "json_output", is_flag=True, help="Output JSON.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    show_default=True,
)
@click.option(
    "--include-attachment-urls",
    is_flag=True,
    help="Include temporary attachment URLs in output.",
)
@click.option(
    "--max-pages",
    default=DEFAULT_MAX_PAGES,
    show_default=True,
    type=int,
    help="Max pagination pages.",
)
def issue_get(url, json_output, output_format, include_attachment_urls, max_pages):
    """Read ONES issue details, comments, custom fields, and attachments."""
    output_format = _resolve_output_format(json_output, output_format)
    max_pages = validate_max_pages(max_pages)
    parsed = parse_ones_issue_url(url)
    config = resolve_config(parsed, require_token=True)
    report = fetch_issue(
        OnesClient(config),
        config,
        parsed,
        max_pages=max_pages,
        include_attachment_urls=include_attachment_urls,
    )
    click.echo(print_payload(report, output_format), nl=False)


@cli.group()
def attachment():
    """Download ONES issue attachments."""


@attachment.command("download")
@click.argument("url")
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, dir_okay=True, path_type=str),
    help="Directory where attachments will be written.",
)
@click.option("--json", "json_output", is_flag=True, help="Output JSON.")
@click.option(
    "--allow-external-attachment-hosts",
    is_flag=True,
    help="Allow attachment downloads from HTTPS hosts outside the ONES host allowlist.",
)
@click.option(
    "--max-pages",
    default=DEFAULT_MAX_PAGES,
    show_default=True,
    type=int,
    help="Max pagination pages.",
)
def attachment_download(
    url,
    output_dir,
    json_output,
    allow_external_attachment_hosts,
    max_pages,
):
    """Download attachments for an ONES issue."""
    max_pages = validate_max_pages(max_pages)
    parsed = parse_ones_issue_url(url)
    config = resolve_config(parsed, require_token=True)
    report = fetch_issue(
        OnesClient(config),
        config,
        parsed,
        max_pages=max_pages,
        include_attachment_urls=True,
    )
    downloaded = download_attachments(
        report,
        output_dir,
        allowed_hosts=[urlparse(config.base_url).hostname],
        allow_external_attachment_hosts=allow_external_attachment_hosts,
    )
    payload = {
        "issueKey": parsed.issue_key,
        "issueID": report["source"]["issueID"],
        "outputDir": output_dir,
        "downloaded": downloaded,
    }
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for item in downloaded:
        click.echo(f"{item['name']}: {item['path']}")


@cli.command()
@click.option("--json", "json_output", is_flag=True, help="Output JSON.")
def doctor(json_output):
    """Check local ONES CLI configuration without printing secrets."""
    payload = doctor_payload()
    if json_output:
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    click.echo(f"ONES_ACCESS_TOKEN: {'set' if payload['tokenConfigured'] else 'missing'}")
    click.echo(f"ONES_BASE_URL: {payload['baseURL'] or '-'}")
    click.echo(f"ONES_TEAM_ID: {payload['teamID'] or '-'}")


def _resolve_output_format(json_output, output_format):
    return "json" if json_output else output_format


def main(argv=None):
    try:
        cli.main(args=argv, prog_name="cli-anything-ones", standalone_mode=False)
    except (UsageError, ApiError, ValueError) as error:
        click.echo(f"[cli-anything-ones] {error}", err=True)
        sys.exit(1)
    except click.ClickException as error:
        error.show()
        sys.exit(error.exit_code)


if __name__ == "__main__":
    main()
