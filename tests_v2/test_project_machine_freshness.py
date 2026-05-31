from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.project import ProjectMachine
from hldspec.state_machine import MachineContext


class _CountingRunner:
    """Counts script invocations; delegates to real bash so the script writes the review."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, command, *, cwd=None, capture=False):
        import subprocess

        parts = [str(c) for c in command]
        script = next((Path(p).name for p in parts if p.endswith(".sh")), parts[0])
        self.calls.append(script)
        proc = subprocess.run(parts, cwd=cwd, text=True,
                              stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.PIPE if capture else None)

        class R:
            returncode = proc.returncode
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

        return R()


# first_run_readonly.sh writes the review marker into <firstrun_dir>/.specify/sync.
FIRST_READONLY = (
    "#!/usr/bin/env bash\nset -euo pipefail\nout=\"$2\"\n"
    "mkdir -p \"$out/.specify/sync\"\n"
    "echo 'Continue to target-spec generation: `true`' > \"$out/.specify/sync/spec_build_plan_review.md\"\n"
)


class ProjectMachineFreshnessTest(unittest.TestCase):
    def _setup(self):
        root = Path(tempfile.mkdtemp())
        repo = root / "repo"
        (repo / "scripts").mkdir(parents=True)
        sh = repo / "scripts" / "first_run_readonly.sh"
        sh.write_text(FIRST_READONLY, encoding="utf-8")
        sh.chmod(sh.stat().st_mode | stat.S_IEXEC)

        ws = root / ".hldspec-first-run"
        ws.mkdir()
        (ws / "HLD.md").write_text("# H\n\n## HLD-001 - A\n\nv1 body.\n", encoding="utf-8")

        runner = _CountingRunner()
        machine = ProjectMachine(runner=runner)
        ctx = MachineContext(repo_root=str(repo), source_hld=str(ws / "HLD.md"), workspace=str(ws))
        return machine, ctx, repo, ws, runner

    def test_rebuilds_absent_then_skips_fresh_then_rebuilds_on_change(self):
        machine, ctx, repo, ws, runner = self._setup()

        machine._ensure_first_readonly(repo, ctx)
        self.assertEqual(runner.calls.count("first_run_readonly.sh"), 1, "build when review absent")

        machine._ensure_first_readonly(repo, ctx)
        self.assertEqual(runner.calls.count("first_run_readonly.sh"), 1, "skip when fresh (review present + fingerprint matches)")

        (ws / "HLD.md").write_text("# H\n\n## HLD-001 - A\n\nv2 CHANGED.\n", encoding="utf-8")
        machine._ensure_first_readonly(repo, ctx)
        self.assertEqual(runner.calls.count("first_run_readonly.sh"), 2, "rebuild when source HLD changed (the stale-skip bug)")


if __name__ == "__main__":
    unittest.main()
