import json
import os
import stat
from urllib.error import HTTPError

import pytest

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
from cli_anything.ones.core.errors import UsageError
from cli_anything.ones.core.formatting import format_bytes
from cli_anything.ones.core.parse import parse_ones_issue_url


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


def test_trusted_ones_hosts():
    assert is_trusted_ones_host("ones.cn")
    assert is_trusted_ones_host("sz.ones.cn")
    assert is_trusted_ones_host("team.myones.net")
    assert not is_trusted_ones_host("example.com")


def test_format_bytes():
    assert format_bytes(10) == "10 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(2 * 1024 * 1024) == "2.0 MB"


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
