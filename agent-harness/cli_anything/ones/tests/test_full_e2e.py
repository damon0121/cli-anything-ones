import json
import os
import shutil
import subprocess
import sys


URL = "https://ones.cn/project/#/team/HbudLR1b/project/JHWX/component/CnWed3jV/sprint/NcAuZo7j/tasks/issue_type/TyjP1WEQ/issue/JHWX-10218"


def _resolve_cli(name):
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.")
    return [sys.executable, "-m", module]


class TestCliSubprocess:
    CLI_BASE = _resolve_cli("cli-anything-ones")

    def _run(self, args, env=None):
        merged_env = os.environ.copy()
        merged_env.update(env or {})
        return subprocess.run(
            self.CLI_BASE + args,
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
