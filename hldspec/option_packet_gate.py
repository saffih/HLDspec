"""Option packet gate — blocks promotion until human-owned decisions are resolved.

When the HLD leaves a source-of-truth, ownership, API, data, rollout, dependency,
split/merge, or security decision unspecified, an OptionPacket is generated.

This module answers: can we proceed, or must the human answer a packet first?

Usage:
    from hldspec.option_packet_gate import OptionPacketQueue, packet_gate_status

    queue = OptionPacketQueue.load(sync_dir / "option_packets.json")
    status = packet_gate_status(queue)
    if not status.ready:
        # block and surface status.blocking_packets
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from hldspec.option_packet import HUMAN_OWNED_DECISION_TYPES, OptionPacket


PACKET_QUEUE_FILENAME = "option_packets.json"


@dataclass
class OptionPacketQueue:
    """Persisted queue of pending and resolved option packets."""
    packets: list[OptionPacket] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "OptionPacketQueue":
        """Load from JSON file; return empty queue if file missing or invalid."""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            packets = [
                OptionPacket(**{k: v for k, v in p.items() if k in OptionPacket.__dataclass_fields__})
                for p in (data.get("packets") or [])
                if isinstance(p, dict)
            ]
            return cls(packets=packets)
        except (json.JSONDecodeError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": 1, "packets": [asdict(p) for p in self.packets]}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def pending(self) -> list[OptionPacket]:
        """Packets not yet answered (no recommended_default accepted and no explicit resolution)."""
        return [p for p in self.packets if not _is_resolved(p)]

    def human_owned_pending(self) -> list[OptionPacket]:
        """Pending packets whose decision_type is in HUMAN_OWNED_DECISION_TYPES."""
        return [p for p in self.pending() if p.decision_type in HUMAN_OWNED_DECISION_TYPES]


def _is_resolved(packet: OptionPacket) -> bool:
    """A packet is resolved when it has been answered.

    Convention: set recommended_default to the chosen option name after
    human approval, or add a resolution note. For now: a non-empty
    recommended_default that matches one of the options means it was accepted.
    """
    if not packet.recommended_default:
        return False
    return packet.recommended_default in packet.options


@dataclass(frozen=True)
class PacketGateStatus:
    ready: bool
    pending_count: int
    human_owned_count: int
    blocking_packets: list[str]   # decision_ids of blocking packets


def packet_gate_status(queue: OptionPacketQueue) -> PacketGateStatus:
    """Return whether the option packet gate is clear.

    Blocks when any human-owned packet is unresolved.
    Packets with no human-owned decision_type do not block (they are inferences).
    """
    blocking = queue.human_owned_pending()
    return PacketGateStatus(
        ready=len(blocking) == 0,
        pending_count=len(queue.pending()),
        human_owned_count=len(blocking),
        blocking_packets=[p.decision_id for p in blocking],
    )
