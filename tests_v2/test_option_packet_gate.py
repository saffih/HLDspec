"""Tests for option_packet_gate — blocks promotion until human-owned decisions resolved.

Critical invariants:
- Human-owned packet with no accepted option blocks the gate.
- Resolved packet (recommended_default in options) does not block.
- Non-human-owned packet type does not block even when unresolved.
- Empty queue is always ready.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.option_packet import make_option_packet
from hldspec.option_packet_gate import (
    OptionPacketQueue,
    PacketGateStatus,
    packet_gate_status,
)


def _unresolved_human_packet(decision_id: str = "DEC-001") -> object:
    return make_option_packet(
        decision_id,
        missing_fact="Who owns the user profile API?",
        options=["ServiceA", "ServiceB"],
        decision_type="api_boundary",  # human-owned
        recommended_default="",        # not yet answered
    )


def _resolved_human_packet(decision_id: str = "DEC-002") -> object:
    return make_option_packet(
        decision_id,
        missing_fact="Who owns the user profile API?",
        options=["ServiceA", "ServiceB"],
        decision_type="api_boundary",
        recommended_default="ServiceA",  # chosen — resolves the packet
    )


def _unresolved_non_human_packet(decision_id: str = "DEC-003") -> object:
    """decision_type not in HUMAN_OWNED_DECISION_TYPES — does not block."""
    from hldspec.option_packet import OptionPacket
    return OptionPacket(
        decision_id=decision_id,
        source_hld_sections=[],
        missing_fact="Which logging level?",
        options=["DEBUG", "INFO"],
        tradeoffs={},
        recommended_default="",
        blast_radius="",
        validation_expectations="",
        affects_constitution=False,
        decision_type="logging_preference",  # not human-owned
    )


class TestPacketGateEmpty(unittest.TestCase):
    def test_empty_queue_is_ready(self):
        queue = OptionPacketQueue()
        status = packet_gate_status(queue)
        self.assertTrue(status.ready)
        self.assertEqual(0, status.human_owned_count)
        self.assertEqual([], status.blocking_packets)

    def test_returns_packet_gate_status_type(self):
        self.assertIsInstance(packet_gate_status(OptionPacketQueue()), PacketGateStatus)


class TestPacketGateBlocking(unittest.TestCase):

    def test_unresolved_human_packet_blocks(self):
        queue = OptionPacketQueue(packets=[_unresolved_human_packet()])
        status = packet_gate_status(queue)
        self.assertFalse(status.ready)
        self.assertEqual(1, status.human_owned_count)
        self.assertIn("DEC-001", status.blocking_packets)

    def test_resolved_human_packet_does_not_block(self):
        queue = OptionPacketQueue(packets=[_resolved_human_packet()])
        status = packet_gate_status(queue)
        self.assertTrue(status.ready)
        self.assertEqual(0, status.human_owned_count)

    def test_non_human_owned_type_does_not_block(self):
        queue = OptionPacketQueue(packets=[_unresolved_non_human_packet()])
        status = packet_gate_status(queue)
        self.assertTrue(status.ready)
        self.assertEqual(0, status.human_owned_count)

    def test_mixed_queue_blocks_when_any_human_owned_unresolved(self):
        queue = OptionPacketQueue(packets=[
            _resolved_human_packet("DEC-R"),
            _unresolved_human_packet("DEC-U"),
            _unresolved_non_human_packet("DEC-N"),
        ])
        status = packet_gate_status(queue)
        self.assertFalse(status.ready)
        self.assertEqual(1, status.human_owned_count)
        self.assertEqual(["DEC-U"], status.blocking_packets)

    def test_multiple_blocking_packets_all_listed(self):
        queue = OptionPacketQueue(packets=[
            _unresolved_human_packet("A"),
            _unresolved_human_packet("B"),
        ])
        status = packet_gate_status(queue)
        self.assertFalse(status.ready)
        self.assertEqual(2, status.human_owned_count)
        self.assertIn("A", status.blocking_packets)
        self.assertIn("B", status.blocking_packets)


class TestOptionPacketQueuePersistence(unittest.TestCase):

    def test_save_and_load_roundtrip(self):
        queue = OptionPacketQueue(packets=[_unresolved_human_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "option_packets.json"
            queue.save(path)
            loaded = OptionPacketQueue.load(path)
        self.assertEqual(1, len(loaded.packets))
        self.assertEqual("DEC-001", loaded.packets[0].decision_id)

    def test_load_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            loaded = OptionPacketQueue.load(Path(d) / "nonexistent.json")
        self.assertEqual([], loaded.packets)

    def test_load_invalid_json_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.json"
            path.write_text("not-json", encoding="utf-8")
            loaded = OptionPacketQueue.load(path)
        self.assertEqual([], loaded.packets)

    def test_saved_file_has_schema_version(self):
        queue = OptionPacketQueue(packets=[_unresolved_human_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "option_packets.json"
            queue.save(path)
            data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(1, data["schema_version"])

    def test_gate_status_after_roundtrip_still_blocks(self):
        queue = OptionPacketQueue(packets=[_unresolved_human_packet()])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "option_packets.json"
            queue.save(path)
            reloaded = OptionPacketQueue.load(path)
        status = packet_gate_status(reloaded)
        self.assertFalse(status.ready)


if __name__ == "__main__":
    unittest.main()
