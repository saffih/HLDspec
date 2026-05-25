from __future__ import annotations

import json
import unittest

from hldspec.reply_parser import parse_reply
from hldspec.state_machine import Checkpoint, CheckpointKind, HumanQuestion


def _make_checkpoint(*questions: HumanQuestion) -> Checkpoint:
    return Checkpoint(
        kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
        blocking_reason="test",
        human_questions=questions,
    )


def _question(question_id: str, options: tuple[str, ...], decision: str = "TBD") -> HumanQuestion:
    return HumanQuestion(
        question_id=question_id,
        title=f"Title for {question_id}",
        question="Choose one.",
        options=options,
        current_decision=decision,
    )


class TestReplyParserContinueShorthands(unittest.TestCase):
    def test_next_no_open_questions_returns_continue(self) -> None:
        cp = _make_checkpoint()
        self.assertEqual("CONTINUE", parse_reply("next", cp))

    def test_ok_no_open_questions_returns_continue(self) -> None:
        cp = _make_checkpoint()
        self.assertEqual("CONTINUE", parse_reply("ok", cp))

    def test_continue_no_open_questions_returns_continue(self) -> None:
        cp = _make_checkpoint()
        self.assertEqual("CONTINUE", parse_reply("continue", cp))

    def test_next_with_open_questions_returns_none(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("KEEP", "SPLIT")))
        self.assertIsNone(parse_reply("next", cp))

    def test_ok_with_open_questions_returns_none(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("KEEP", "SPLIT")))
        self.assertIsNone(parse_reply("ok", cp))


class TestReplyParserAcceptAll(unittest.TestCase):
    def test_accept_all_all_questions_have_accept_option(self) -> None:
        cp = _make_checkpoint(
            _question("Q-001", ("ACCEPT", "REJECT")),
            _question("Q-002", ("APPROVE_ALL", "DECLINE")),
        )
        result = parse_reply("accept all", cp)
        assert result is not None
        mapping = json.loads(result)
        self.assertEqual({"Q-001": "ACCEPT", "Q-002": "APPROVE_ALL"}, mapping)

    def test_accept_all_question_without_accept_returns_none(self) -> None:
        cp = _make_checkpoint(
            _question("Q-001", ("ACCEPT", "REJECT")),
            _question("Q-002", ("KEEP", "SPLIT")),
        )
        self.assertIsNone(parse_reply("accept all", cp))

    def test_accept_all_no_open_questions_returns_empty_json(self) -> None:
        cp = _make_checkpoint()
        result = parse_reply("accept all", cp)
        self.assertEqual("{}", result)

    def test_accept_all_picks_first_accept_option(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("REJECT", "ACCEPT_PARTIAL", "ACCEPT_ALL")))
        result = parse_reply("accept all", cp)
        assert result is not None
        mapping = json.loads(result)
        self.assertEqual("ACCEPT_PARTIAL", mapping["Q-001"])


class TestReplyParserExactOptionMatch(unittest.TestCase):
    def test_exact_option_match_single_open_question(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("KEEP_AS_ONE", "SPLIT")))
        self.assertEqual("KEEP_AS_ONE", parse_reply("KEEP_AS_ONE", cp))

    def test_exact_option_match_case_insensitive(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("KEEP_AS_ONE", "SPLIT")))
        self.assertEqual("KEEP_AS_ONE", parse_reply("keep_as_one", cp))

    def test_exact_option_match_multiple_open_questions_returns_none(self) -> None:
        cp = _make_checkpoint(
            _question("Q-001", ("KEEP_AS_ONE", "SPLIT")),
            _question("Q-002", ("YES", "NO")),
        )
        self.assertIsNone(parse_reply("KEEP_AS_ONE", cp))

    def test_unrecognised_string_returns_none(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("KEEP_AS_ONE", "SPLIT")))
        self.assertIsNone(parse_reply("something random", cp))


class TestReplyParserWhitespaceAndCase(unittest.TestCase):
    def test_whitespace_stripped_from_continue_shorthand(self) -> None:
        cp = _make_checkpoint()
        self.assertEqual("CONTINUE", parse_reply("  ok  ", cp))

    def test_mixed_case_continue_shorthand(self) -> None:
        cp = _make_checkpoint()
        self.assertEqual("CONTINUE", parse_reply("Next", cp))

    def test_whitespace_stripped_from_option(self) -> None:
        cp = _make_checkpoint(_question("Q-001", ("KEEP_AS_ONE", "SPLIT")))
        self.assertEqual("KEEP_AS_ONE", parse_reply("  KEEP_AS_ONE  ", cp))

    def test_unrecognised_empty_string_returns_none(self) -> None:
        cp = _make_checkpoint()
        self.assertIsNone(parse_reply("", cp))


if __name__ == "__main__":
    unittest.main()
