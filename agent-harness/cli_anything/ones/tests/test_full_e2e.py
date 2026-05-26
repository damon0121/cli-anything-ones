import json
import os
import shutil
import subprocess
import sys


URL = "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/component/CnWed3jV/sprint/NcAuZo7j/tasks/issue_type/TyjP1WEQ/issue/JHWX-10218"


def _resolve_cli(name):
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if force:
        if path:
            return [path]
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.")
    return [sys.executable, "-m", module]


class TestCliSubprocess:
    CLI_BASE = _resolve_cli("cli-anything-ones")

    def _run(self, args, env=None, input=None):
        merged_env = os.environ.copy()
        merged_env.update(env or {})
        return subprocess.run(
            self.CLI_BASE + args,
            input=input,
            capture_output=True,
            text=True,
            check=True,
            env=merged_env,
        )

    def test_help(self):
        result = self._run(["--help"])

        assert "Read-only CLI-Anything harness for ONES issues" in result.stdout

    def test_issue_parse_json(self):
        result = self._run(["issue", "parse", URL, "--json"])
        payload = json.loads(result.stdout)

        assert payload["issueKey"] == "JHWX-10218"
        assert payload["teamID"] == "HbudLR1b"

    def test_issue_list_help(self):
        result = self._run(["issue", "list", "--help"])

        assert "List ONES issues" in result.stdout
        assert "--exclude-status" in result.stdout
        assert "--assignee-id" in result.stdout
        assert "--mine" in result.stdout

    def test_config_set_token_from_stdin(self, tmp_path):
        env = {"XDG_CONFIG_HOME": str(tmp_path), "ONES_ACCESS_TOKEN": ""}

        result = self._run(["config", "set-token", "--stdin"], env=env, input="saved-token\n")
        doctor = self._run(["doctor", "--json"], env=env)
        payload = json.loads(doctor.stdout)

        assert "Saved ONES_ACCESS_TOKEN" in result.stdout
        assert payload["tokenConfigured"] is True
        assert payload["tokenSource"] == "local_config"
