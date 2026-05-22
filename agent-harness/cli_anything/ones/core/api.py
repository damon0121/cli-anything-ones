import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import ApiError, UsageError


class OnesClient:
    def __init__(self, config):
        if not config.token:
            raise UsageError(
                "ONES_ACCESS_TOKEN is required. Create a read-only ONES OpenAPI token and export it before running this command."
            )
        self.config = config

    def request(self, pathname: str, params=None):
        params = {
            key: value
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.config.api_base_url}{pathname}{query}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.config.token}",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                body_text = response.read().decode("utf-8", errors="replace")
                status = response.status
        except HTTPError as error:
            body_text = error.read().decode("utf-8", errors="replace")
            body = _parse_json_response(body_text, pathname, error.code)
            _raise_api_error(body, error.code, error.reason or "ONES API request failed")

        body = _parse_json_response(body_text, pathname, status)
        if _is_fail_result(body):
            _raise_api_error(body, status, f"ONES API request failed: {pathname}")
        return body


def _parse_json_response(body_text: str, pathname: str, status: int):
    if not body_text:
        return {}
    try:
        return json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise ApiError(
            f"ONES API returned non-JSON response for {pathname}.", status=status
        ) from exc


def _is_fail_result(body) -> bool:
    return isinstance(body.get("result"), str) and body["result"].upper() == "FAIL"


def _raise_api_error(body, status, fallback_message):
    error_code = body.get("errorCode") if isinstance(body, dict) else None
    error_msg = body.get("errorMsg") if isinstance(body, dict) else None
    raise ApiError(
        error_msg or fallback_message,
        status=status,
        error_code=error_code,
        error_msg=error_msg,
    )


def is_not_found(error: Exception) -> bool:
    return isinstance(error, ApiError) and (
        error.status == 404 or error.error_code == "NotFound"
    )


def is_invalid_project_filter(error: Exception) -> bool:
    return (
        isinstance(error, ApiError)
        and error.error_code == "InvalidParameter"
        and "projectID" in (error.error_msg or str(error))
    )
