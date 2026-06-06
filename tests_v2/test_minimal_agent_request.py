from __future__ import annotations

import unittest

from hldspec.minimal_agent_request import detect_workflow_trigger, parse_minimal_agent_request


class MinimalAgentRequestParserTests(unittest.TestCase):
    def test_parses_hld_create_shape(self) -> None:
        parsed = parse_minimal_agent_request(
            "HLDspec HLD: /tmp/Flow-HLD.md create /tmp/flow-target runtime claude"
        )
        self.assertEqual("/tmp/Flow-HLD.md", parsed.source_hld)
        self.assertEqual("/tmp/flow-target", parsed.target_workspace)
        self.assertEqual("create", parsed.mode)
        self.assertEqual("claude", parsed.runtime)

    def test_parses_create_from_shape(self) -> None:
        parsed = parse_minimal_agent_request(
            "HLDspec create /tmp/flow-target from /tmp/Flow-HLD.md runtime codex"
        )
        self.assertEqual("/tmp/Flow-HLD.md", parsed.source_hld)
        self.assertEqual("/tmp/flow-target", parsed.target_workspace)
        self.assertEqual("codex", parsed.runtime)

    def test_parses_quoted_paths_with_spaces(self) -> None:
        parsed = parse_minimal_agent_request(
            'HLDspec HLD: "/tmp/Flow HLD.md" create "/tmp/flow target" Build Loop init runtime codex'
        )
        self.assertEqual("/tmp/Flow HLD.md", parsed.source_hld)
        self.assertEqual("/tmp/flow target", parsed.target_workspace)
        self.assertEqual("build_loop_init", parsed.workflow_trigger)

    def test_parses_copy_ready_one_liner_with_quoted_paths(self) -> None:
        parsed = parse_minimal_agent_request(
            'Use HLDspec with source HLD: "/tmp/Flow HLD.md" and target project: "/tmp/flow target". '
            "Prepare the target, check SpecKit readiness, and report STATUS, blockers, evidence, and next safe action."
        )
        self.assertEqual("/tmp/Flow HLD.md", parsed.source_hld)
        self.assertEqual("/tmp/flow target", parsed.target_workspace)

    def test_parses_target_label_shape(self) -> None:
        parsed = parse_minimal_agent_request(
            "HLDspec HLD: /tmp/Flow-HLD.md target: /tmp/flow-target runtime: devin"
        )
        self.assertEqual("/tmp/Flow-HLD.md", parsed.source_hld)
        self.assertEqual("/tmp/flow-target", parsed.target_workspace)
        self.assertEqual("devin", parsed.runtime)

    def test_parses_copy_ready_one_liner(self) -> None:
        parsed = parse_minimal_agent_request(
            "Use HLDspec with source HLD: /tmp/Flow-HLD.md and target project: /tmp/flow-target. "
            "Prepare the target, check SpecKit readiness, and report STATUS, blockers, evidence, and next safe action. "
            "Do not implement or run SpecKit unless HLDspec says it is safe."
        )
        self.assertEqual("/tmp/Flow-HLD.md", parsed.source_hld)
        self.assertEqual("/tmp/flow-target", parsed.target_workspace)
        self.assertEqual("claude", parsed.runtime)

    def test_detects_check_hld_trigger(self) -> None:
        parsed = parse_minimal_agent_request(
            "HLDspec HLD: /tmp/Flow-HLD.md create /tmp/flow-target check HLD runtime claude"
        )
        self.assertEqual("check_hld", parsed.workflow_trigger)

    def test_detects_build_loop_triggers(self) -> None:
        prereqs = parse_minimal_agent_request(
            "HLDspec HLD: /tmp/Flow-HLD.md create /tmp/flow-target Build Loop prereqs"
        )
        init = parse_minimal_agent_request(
            "HLDspec HLD: /tmp/Flow-HLD.md create /tmp/flow-target Build Loop init"
        )
        ready = parse_minimal_agent_request(
            "HLDspec HLD: /tmp/Flow-HLD.md create /tmp/flow-target Build Loop ready"
        )
        self.assertEqual("build_loop_prereqs", prereqs.workflow_trigger)
        self.assertEqual("build_loop_init", init.workflow_trigger)
        self.assertEqual("build_loop_ready", ready.workflow_trigger)

    def test_shared_trigger_detector(self) -> None:
        self.assertEqual("check_hld", detect_workflow_trigger("please check HLD"))
        self.assertEqual("build_loop_prereqs", detect_workflow_trigger("Build Loop prereqs"))
        self.assertEqual("build_loop_init", detect_workflow_trigger("Build Loop init"))
        self.assertEqual("build_loop_ready", detect_workflow_trigger("Build Loop ready"))

    def test_negated_trigger_detector_does_not_activate_workflow(self) -> None:
        self.assertIsNone(detect_workflow_trigger("do not check HLD yet"))
        self.assertIsNone(detect_workflow_trigger("continue without Build Loop ready"))
        self.assertIsNone(detect_workflow_trigger("don't do Build Loop ready yet"))
        self.assertIsNone(detect_workflow_trigger("please do not do Build Loop prereqs first"))
        self.assertIsNone(detect_workflow_trigger("without doing Build Loop ready"))

    def test_trigger_detector_keeps_positive_trigger_when_other_trigger_is_negated(self) -> None:
        self.assertEqual(
            "build_loop_ready",
            detect_workflow_trigger("Build Loop ready, do not run Build Loop init separately"),
        )
        self.assertIsNone(detect_workflow_trigger("Build Loop ready after check HLD"))

    def test_parser_rejects_multiple_positive_workflow_triggers(self) -> None:
        with self.assertRaises(ValueError):
            parse_minimal_agent_request(
                "HLDspec HLD: /tmp/Flow-HLD.md create /tmp/flow-target Build Loop ready after check HLD"
            )

    def test_rejects_unrecognized_request(self) -> None:
        with self.assertRaises(ValueError):
            parse_minimal_agent_request("hello world")


if __name__ == "__main__":
    unittest.main()
