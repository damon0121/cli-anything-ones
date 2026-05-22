import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .errors import UsageError


@dataclass(frozen=True)
class OnesConfig:
    base_url: str
    api_base_url: str
    team_id: str
    token: str | None


def resolve_config(parsed, require_token=True) -> OnesConfig:
    configured_base_url = os.environ.get("ONES_BASE_URL")
    if configured_base_url:
        base_url = normalize_base_url(configured_base_url)
        assert_trusted_base_url(base_url, is_explicit=True)
    else:
        origin = normalize_base_url(parsed.origin)
        assert_trusted_base_url(origin, is_explicit=False)
        base_url = discover_base_url(parsed)
        assert_trusted_base_url(base_url, is_explicit=False)

    team_id = os.environ.get("ONES_TEAM_ID") or parsed.team_id
    if not team_id:
        raise UsageError("ONES_TEAM_ID is required because no team ID was found in the URL.")

    token = os.environ.get("ONES_ACCESS_TOKEN")
    if require_token and not token:
        raise UsageError(
            "ONES_ACCESS_TOKEN is required. Create a read-only ONES OpenAPI token and export it before running this command."
        )

    return OnesConfig(
        base_url=base_url,
        api_base_url=f"{base_url}/openapi/v2",
        team_id=team_id,
        token=token,
    )


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise UsageError(f"Invalid ONES base URL: {value}")
    return f"{parsed.scheme}://{parsed.netloc}"


def discover_base_url(parsed) -> str:
    origin = normalize_base_url(parsed.origin)
    headers = {}
    if parsed.team_id:
        headers["Cookie"] = f"ones-team-uuid={parsed.team_id}; ones-org-extractor=extracted"

    try:
        request = Request(f"{origin}/project/", headers=headers)
        with urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8", errors="replace")
        match = re.search(r'"regionBaseUrl"\s*:\s*"([^"]+)"', text)
        if match:
            return normalize_base_url(match.group(1))
    except Exception:
        pass

    return origin


def assert_trusted_base_url(base_url: str, is_explicit: bool) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https":
        raise UsageError("ONES_BASE_URL and issue URL must use https.")

    if not is_explicit and not is_trusted_ones_host(parsed.hostname or ""):
        raise UsageError(
            f"Refusing to send ONES_ACCESS_TOKEN to untrusted host {parsed.hostname}. Set ONES_BASE_URL explicitly for self-hosted ONES domains."
        )


def is_trusted_ones_host(hostname: str) -> bool:
    return (
        hostname == "ones.cn"
        or hostname.endswith(".ones.cn")
        or hostname.endswith(".myones.net")
    )


def doctor_payload() -> dict:
    base_url = os.environ.get("ONES_BASE_URL")
    return {
        "tokenConfigured": bool(os.environ.get("ONES_ACCESS_TOKEN")),
        "baseURL": base_url,
        "teamID": os.environ.get("ONES_TEAM_ID"),
        "baseURLTrusted": _base_url_trusted(base_url) if base_url else None,
    }


def _base_url_trusted(base_url: str) -> bool:
    try:
        normalized = normalize_base_url(base_url)
        assert_trusted_base_url(normalized, is_explicit=True)
        return True
    except UsageError:
        return False
