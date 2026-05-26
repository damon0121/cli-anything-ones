import json
import os
import stat
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from cli_anything.ones.core.auth import current_user_id
from cli_anything.ones.core.attachments import (
    _open_attachment_response,
    _safe_filename,
    _validate_attachment_url,
)
from cli_anything.ones.core.config import (
    doctor_payload,
    is_trusted_ones_host,
    resolve_config,
    save_access_token,
)
from cli_anything.ones.core.errors import ApiError, UsageError
from cli_anything.ones.core.formatting import format_bytes
from cli_anything.ones.core.issues import PAGE_LIMIT, fetch_issue_list, validate_issue_list_limit
from cli_anything.ones.core.parse import parse_ones_issue_url, parse_ones_url


URL = "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/component/CnWed3jV/sprint/NcAuZo7j/tasks/issue_type/TyjP1WEQ/issue/JHWX-10218"


def test_parse_ones_hash_issue_url():
    parsed = parse_ones_issue_url(URL)

    assert parsed.origin == "https://ones.cn"
    assert parsed.team_id == "HbudLR1b"
    assert parsed.project_id == "JHWX"
    assert parsed.component_id == "CnWed3jV"
    assert parsed.sprint_id == "NcAuZo7j"
    assert parsed.issue_type_id == "TyjP1WEQ"
    assert parsed.issue_key == "JHWX-10218"
    assert parsed.issue_number == 10218
    assert parsed.project_key == "JHWX"


def test_parsed_issue_url_to_dict_is_json_serializable():
    payload = parse_ones_issue_url(URL).to_dict()

    assert json.loads(json.dumps(payload))["issueKey"] == "JHWX-10218"


def test_parse_ones_project_url_without_issue_key():
    parsed = parse_ones_url("https://ones.cn/project/#/team/HbudLR1b/project/JHWX")

    assert parsed.team_id == "HbudLR1b"
    assert parsed.project_id == "JHWX"
    assert parsed.issue_key is None
    assert parsed.issue_number is None
    assert parsed.project_key == "JHWX"


def test_trusted_ones_hosts():
    assert is_trusted_ones_host("ones.cn")
    assert is_trusted_ones_host("sz.ones.cn")
    assert is_trusted_ones_host("team.myones.net")
    assert not is_trusted_ones_host("example.com")


def test_format_bytes():
    assert format_bytes(10) == "10 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(2 * 1024 * 1024) == "2.0 MB"


def test_fetch_issue_list_paginates_and_normalizes_items():
    class FakeClient:
        def __init__(self):
            self.requests = []

        def request(self, pathname, params):
            self.requests.append((pathname, params))
            if params.get("cursor") is None:
                return {
                    "data": {
                        "list": [
                            {
                                "id": "issue-1",
                                "number": 1,
                                "title": "First issue",
                                "status": {"id": "open", "name": "Open"},
                                "assignee": {"id": "u1", "name": "Owner"},
                            },
                            {"id": "issue-2", "number": 2, "title": "Second issue"},
                        ],
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    }
                }
            return {
                "data": {
                    "list": [{"id": "issue-3", "number": 3, "title": "Third issue"}],
                    "pageInfo": {"hasNextPage": False},
                }
            }

    client = FakeClient()
    config = SimpleNamespace(base_url="https://sz.ones.cn", team_id="HbudLR1b")
    parsed = parse_ones_url(URL)

    report = fetch_issue_list(client, config, parsed, limit=3, max_pages=5)

    assert report["source"]["projectID"] == "JHWX"
    assert report["source"]["componentID"] == "CnWed3jV"
    assert report["source"]["sprintID"] == "NcAuZo7j"
    assert report["source"]["issueTypeID"] == "TyjP1WEQ"
    assert report["issues"][0]["key"] == "JHWX-1"
    assert report["issues"][0]["status"] == {"id": "open", "name": "Open"}
    assert report["pageInfo"] == {"count": 3, "hasMore": False}
    assert client.requests[0][0] == "/project/issues"
    assert client.requests[0][1]["componentID"] == "CnWed3jV"
    assert client.requests[0][1]["sprintID"] == "NcAuZo7j"
    assert client.requests[0][1]["limit"] == PAGE_LIMIT
    assert client.requests[1][1]["cursor"] == "cursor-1"


def test_fetch_issue_list_filters_sprint_from_response_items():
    class FakeClient:
        def request(self, _pathname, params):
            if params.get("cursor") is None:
                return {
                    "data": {
                        "list": [
                            {
                                "id": "wrong-sprint",
                                "number": 1,
                                "title": "Wrong sprint",
                                "sprint": {"id": "other"},
                            },
                            {
                                "id": "right-sprint",
                                "number": 2,
                                "title": "Right sprint",
                                "sprint": {"id": "NcAuZo7j"},
                            },
                        ],
                        "pageInfo": {"hasNextPage": False},
                    }
                }
            raise AssertionError("unexpected page")

    config = SimpleNamespace(base_url="https://sz.ones.cn", team_id="HbudLR1b")
    parsed = parse_ones_url(URL)

    report = fetch_issue_list(FakeClient(), config, parsed, limit=10, max_pages=5)

    assert [issue["id"] for issue in report["issues"]] == ["right-sprint"]


def test_fetch_issue_list_excludes_status_and_continues_pagination():
    class FakeClient:
        def __init__(self):
            self.requests = []

        def request(self, pathname, params):
            self.requests.append((pathname, params))
            if params.get("cursor") is None:
                return {
                    "data": {
                        "list": [
                            {
                                "id": "closed-by-name",
                                "number": 1,
                                "status": {"id": "closed-id", "name": "关闭"},
                            },
                            {
                                "id": "closed-by-id",
                                "number": 2,
                                "status": {"id": "done-id", "name": "Done"},
                            },
                            {
                                "id": "open-1",
                                "number": 3,
                                "status": {"id": "open-id", "name": "待处理"},
                            },
                        ],
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    }
                }
            return {
                "data": {
                    "list": [
                        {
                            "id": "open-2",
                            "number": 4,
                            "status": {"id": "open-id", "name": "处理中"},
                        }
                    ],
                    "pageInfo": {"hasNextPage": False},
                }
            }

    client = FakeClient()
    config = SimpleNamespace(base_url="https://sz.ones.cn", team_id="HbudLR1b")
    parsed = parse_ones_url("https://ones.cn/project/#/team/HbudLR1b/project/JHWX")

    report = fetch_issue_list(
        client,
        config,
        parsed,
        exclude_statuses=("关闭", "done-id"),
        limit=2,
        max_pages=5,
    )

    assert [issue["id"] for issue in report["issues"]] == ["open-1", "open-2"]
    assert report["pageInfo"] == {"count": 2, "hasMore": False}
    assert client.requests[0][1]["limit"] == PAGE_LIMIT
    assert client.requests[1][1]["cursor"] == "cursor-1"


def test_fetch_issue_list_filters_assignee_and_continues_pagination():
    class FakeClient:
        def __init__(self):
            self.requests = []

        def request(self, pathname, params):
            self.requests.append((pathname, params))
            if params.get("cursor") is None:
                return {
                    "data": {
                        "list": [
                            {
                                "id": "other-user",
                                "number": 1,
                                "assignee": {"id": "other", "name": "Other"},
                            },
                            {
                                "id": "mine-1",
                                "number": 2,
                                "assignee": {"id": "Uu13cX5m", "name": "邓铭"},
                            },
                        ],
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    }
                }
            return {
                "data": {
                    "list": [
                        {
                            "id": "mine-2",
                            "number": 3,
                            "assigneeID": "Uu13cX5m",
                        }
                    ],
                    "pageInfo": {"hasNextPage": False},
                }
            }

    client = FakeClient()
    config = SimpleNamespace(base_url="https://sz.ones.cn", team_id="HbudLR1b")
    parsed = parse_ones_url("https://ones.cn/project/#/team/HbudLR1b/project/JHWX")

    report = fetch_issue_list(
        client,
        config,
        parsed,
        assignee_id="Uu13cX5m",
        limit=2,
        max_pages=5,
    )

    assert report["source"]["assigneeID"] == "Uu13cX5m"
    assert [issue["id"] for issue in report["issues"]] == ["mine-1", "mine-2"]
    assert report["pageInfo"] == {"count": 2, "hasMore": False}
    assert client.requests[0][1]["limit"] == PAGE_LIMIT
    assert client.requests[1][1]["cursor"] == "cursor-1"


def test_fetch_issue_list_drops_invalid_project_id_filter():
    class FakeClient:
        def __init__(self):
            self.requests = []

        def request(self, pathname, params):
            self.requests.append((pathname, params))
            if params.get("projectID") == "JHWX":
                raise ApiError(
                    "issue projectID invalidFormat",
                    error_code="InvalidParameter",
                    error_msg="issue projectID invalidFormat",
                )
            return {
                "data": {
                    "list": [{"id": "issue-1", "number": 1, "title": "First issue"}],
                    "pageInfo": {"hasNextPage": False},
                }
            }

    config = SimpleNamespace(base_url="https://sz.ones.cn", team_id="HbudLR1b")
    parsed = parse_ones_url(URL)

    report = fetch_issue_list(FakeClient(), config, parsed, limit=10, max_pages=5)

    assert report["source"]["projectID"] is None
    assert report["source"]["componentID"] == "CnWed3jV"
    assert report["source"]["sprintID"] == "NcAuZo7j"
    assert report["issues"][0]["key"] == "JHWX-1"
    assert report["warnings"] == [
        "Dropped projectID filter JHWX because ONES rejected it as invalid."
    ]


def test_validate_issue_list_limit_rejects_non_positive_value():
    with pytest.raises(ValueError):
        validate_issue_list_limit(0)


def test_resolve_config_rejects_untrusted_origin_before_network(monkeypatch):
    called = False

    def fail_if_called(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("network should not be called")

    monkeypatch.setattr("cli_anything.ones.core.config.urlopen", fail_if_called)
    parsed = parse_ones_issue_url("https://example.com/project/#/team/T/issue/ABC-1")

    with pytest.raises(UsageError):
        resolve_config(parsed, require_token=False)

    assert called is False


def test_resolve_config_uses_saved_token(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("ONES_BASE_URL", "https://sz.ones.cn")
    monkeypatch.delenv("ONES_ACCESS_TOKEN", raising=False)
    save_access_token("saved-token")

    config = resolve_config(parse_ones_issue_url(URL), require_token=True)

    assert config.token == "saved-token"


def test_resolve_config_without_token_ignores_saved_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("ONES_BASE_URL", "https://sz.ones.cn")
    monkeypatch.delenv("ONES_ACCESS_TOKEN", raising=False)
    config_path = tmp_path / "cli-anything-ones" / "config.json"
    config_path.parent.mkdir()
    config_path.write_text("{", encoding="utf-8")

    config = resolve_config(parse_ones_issue_url(URL), require_token=False)

    assert config.token is None


def test_environment_token_overrides_saved_token(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("ONES_BASE_URL", "https://sz.ones.cn")
    save_access_token("saved-token")
    monkeypatch.setenv("ONES_ACCESS_TOKEN", "env-token")

    config = resolve_config(parse_ones_issue_url(URL), require_token=True)

    assert config.token == "env-token"


def test_save_access_token_uses_private_file_permissions(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    path = save_access_token("saved-token")

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_doctor_reports_saved_token_source(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("ONES_ACCESS_TOKEN", raising=False)
    save_access_token("saved-token")

    payload = doctor_payload()

    assert payload["tokenConfigured"] is True
    assert payload["tokenSource"] == "local_config"


def test_current_user_id_uses_oauth_introspection(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"active": true, "sub": "Uu13cX5m"}'

    def fake_urlopen(request, timeout):
        assert request.full_url == "https://sz.ones.cn/oauth2/introspect"
        assert request.get_header("Authorization") == "Bearer token"
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr("cli_anything.ones.core.auth.urlopen", fake_urlopen)
    config = SimpleNamespace(base_url="https://sz.ones.cn", token="token")

    assert current_user_id(config) == "Uu13cX5m"


def test_current_user_id_rejects_inactive_token(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"active": false}'

    monkeypatch.setattr(
        "cli_anything.ones.core.auth.urlopen",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    config = SimpleNamespace(base_url="https://sz.ones.cn", token="token")

    with pytest.raises(ApiError):
        current_user_id(config)


def test_attachment_url_validation_rejects_untrusted_hosts():
    with pytest.raises(UsageError):
        _validate_attachment_url("https://example.com/file.png", allowed_hosts=["sz.ones.cn"])


def test_attachment_url_validation_allows_configured_host():
    _validate_attachment_url(
        "https://self-hosted.ones.example/file.png",
        allowed_hosts=["self-hosted.ones.example"],
    )


def test_safe_filename_removes_path_separators():
    assert _safe_filename("../a/b.png") == "-a-b.png"


def test_attachment_redirect_target_is_validated(monkeypatch):
    class FakeHeaders(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    class FakeOpener:
        def open(self, request, timeout):
            raise HTTPError(
                request.full_url,
                302,
                "Found",
                FakeHeaders({"Location": "https://example.com/file.png"}),
                None,
            )

    monkeypatch.setattr(
        "cli_anything.ones.core.attachments._NO_REDIRECT_OPENER",
        FakeOpener(),
    )

    with pytest.raises(UsageError):
        _open_attachment_response("https://sz.ones.cn/file.png", allowed_hosts=["sz.ones.cn"])
