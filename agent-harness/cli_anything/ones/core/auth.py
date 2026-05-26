import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .errors import ApiError, UsageError


def current_user_id(config) -> str:
    if not config.token:
        raise UsageError("ONES_ACCESS_TOKEN is required to resolve the current user.")

    pathname = "/oauth2/introspect"
    request = Request(
        f"{config.base_url}{pathname}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.token}",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            body_text = response.read().decode("utf-8", errors="replace")
            status = response.status
    except HTTPError as error:
        body_text = error.read().decode("utf-8", errors="replace")
        body = _parse_json_response(body_text, pathname, error.code)
        raise ApiError(
            body.get("error_description") or body.get("error") or "ONES token introspection failed.",
            status=error.code,
            error_code=body.get("error"),
            error_msg=body.get("error_description"),
        ) from error

    body = _parse_json_response(body_text, pathname, status)
    if not body.get("active"):
        raise ApiError("ONES access token is not active.", status=status)

    user_id = body.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise ApiError("ONES token introspection did not return a user ID.", status=status)
    return user_id.strip()


def _parse_json_response(body_text: str, pathname: str, status: int):
    if not body_text:
        return {}
    try:
        body = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise ApiError(
            f"ONES API returned non-JSON response for {pathname}.", status=status
        ) from exc
    if not isinstance(body, dict):
        raise ApiError(
            f"ONES API returned unexpected response for {pathname}.", status=status
        )
    return body
