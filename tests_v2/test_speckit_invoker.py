import unittest
from pathlib import Path

from hldspec.command_runner import CommandResult
from hldspec.speckit_invoker import SpecKitInvoker, build_prompt


class FakeRunner:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.calls = []

    def run(self, command, *, cwd=None, capture=False):
        self.calls.append({"command": list(command), "cwd": cwd, "capture": capture})
        return CommandResult(
            returncode=self.returncode,
            command=tuple(str(c) for c in command),
            stdout="ok",
            stderr="",
        )


class InvokerCommandTests(unittest.TestCase):
    # No-op change detector so runner.calls holds only the speckit command,
    # not the git-signature probes.
    NOOP = staticmethod(lambda d: "sig")

    def test_builds_skip_permissions_command(self):
        runner = FakeRunner()
        inv = SpecKitInvoker("/tmp/proj", runner=runner, change_detector=self.NOOP)
        result = inv.invoke("SPECIFY", "Build the thing")
        self.assertTrue(result.ok)
        self.assertEqual(result.skill, "speckit-specify")
        cmd = runner.calls[0]["command"]
        self.assertIn("--dangerously-skip-permissions", cmd)
        self.assertEqual(cmd[-1], "/speckit-specify Build the thing")
        self.assertEqual(runner.calls[0]["cwd"], Path("/tmp/proj"))

    def test_routes_model_per_phase(self):
        runner = FakeRunner()
        inv = SpecKitInvoker("/tmp/proj", runner=runner, change_detector=self.NOOP)
        inv.invoke("TASKS", "x")
        cmd = runner.calls[0]["command"]
        self.assertIn("--model", cmd)
        self.assertEqual(cmd[cmd.index("--model") + 1], "haiku")  # routine -> cheap

    def test_can_disable_skip_permissions(self):
        runner = FakeRunner()
        inv = SpecKitInvoker("/tmp/proj", runner=runner, skip_permissions=False, change_detector=self.NOOP)
        inv.invoke("PLAN", "plan it")
        self.assertNotIn("--dangerously-skip-permissions", runner.calls[0]["command"])

    def test_phase_skill_mapping(self):
        runner = FakeRunner()
        inv = SpecKitInvoker("/tmp/p", runner=runner, change_detector=self.NOOP)
        self.assertEqual(inv.invoke("CONSTITUTION", "x").skill, "speckit-constitution")
        self.assertEqual(inv.invoke("TASKS", "x").skill, "speckit-tasks")
        self.assertEqual(inv.invoke("IMPLEMENT", "x").skill, "speckit-implement")

    def test_unknown_phase_fails(self):
        runner = FakeRunner()
        inv = SpecKitInvoker("/tmp/p", runner=runner, change_detector=self.NOOP)
        result = inv.invoke("BOGUS", "x")
        self.assertFalse(result.ok)
        self.assertEqual(result.returncode, 2)

    def test_nonzero_returncode_not_ok(self):
        runner = FakeRunner(returncode=1)
        inv = SpecKitInvoker("/tmp/p", runner=runner, change_detector=self.NOOP)
        self.assertFalse(inv.invoke("SPECIFY", "x").ok)


class ArtifactVerificationTests(unittest.TestCase):
    """The anti-hollow-completion gate: exit 0 alone must not count as done."""

    def _invoker(self, returncode, signatures):
        """signatures: list consumed by the fake change_detector on each call."""
        runner = FakeRunner(returncode=returncode)
        seq = list(signatures)
        det = lambda d: seq.pop(0) if seq else "x"
        return SpecKitInvoker("/tmp/proj", runner=runner, change_detector=det)

    def test_artifact_phase_with_change_is_verified(self):
        inv = self._invoker(0, ["before", "after"])  # changed
        result = inv.invoke("SPECIFY", "x")
        self.assertTrue(result.ok)
        self.assertTrue(result.produced_artifacts)
        self.assertTrue(result.verified)

    def test_artifact_phase_without_change_not_verified(self):
        inv = self._invoker(0, ["same", "same"])  # no change despite exit 0
        result = inv.invoke("IMPLEMENT", "x")
        self.assertTrue(result.ok)
        self.assertFalse(result.produced_artifacts)
        self.assertFalse(result.verified)  # hollow completion blocked

    def test_nonartifact_phase_verified_on_ok_without_change(self):
        inv = self._invoker(0, ["same", "same"])
        result = inv.invoke("ANALYZE", "x")  # analyze need not produce files
        self.assertTrue(result.verified)

    def test_failed_command_never_verified(self):
        inv = self._invoker(1, ["before", "after"])
        result = inv.invoke("SPECIFY", "x")
        self.assertFalse(result.verified)


class BuildPromptTests(unittest.TestCase):
    def test_uses_specify_input_and_omits_hld(self):
        feature = {
            "feature_id": "027",
            "feature_name": "v1 Scope Definition",
            "speckit_specify_input": "Build v1 Scope Definition.",
        }
        prompt = build_prompt("SPECIFY", feature)
        self.assertIn("Build v1 Scope Definition.", prompt)
        self.assertNotIn("flow-hld.md", prompt)

    def test_includes_architecture_context(self):
        feature = {
            "feature_id": "010",
            "feature_name": "DB API",
            "speckit_specify_input": "Build DB API.",
            "architecture_context": {
                "contracts": [
                    {
                        "contract_id": "DATABASE_API_CONTRACT",
                        "contract_name": "Database API Contract",
                        "provider": "HTTP API layer",
                        "consumer": "Web UI",
                        "source_of_truth": "SQLite",
                    }
                ],
                "data_objects": [],
            },
        }
        prompt = build_prompt("SPECIFY", feature)
        self.assertIn("DATABASE_API_CONTRACT", prompt)
        self.assertIn("Database API Contract", prompt)

    def test_implement_phase_adds_implementation_guidance(self):
        feature = {"feature_id": "010", "feature_name": "DB", "speckit_specify_input": "x"}
        prompt = build_prompt("IMPLEMENT", feature)
        self.assertIn("add tests", prompt)

    def test_constitution_summary_included(self):
        feature = {"feature_id": "010", "feature_name": "DB", "speckit_specify_input": "x"}
        prompt = build_prompt("PLAN", feature, constitution_summary="Rule: SQLite is SoT.")
        self.assertIn("SQLite is SoT", prompt)


if __name__ == "__main__":
    unittest.main()
