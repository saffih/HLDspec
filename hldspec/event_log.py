"""Event log — durable event history for debugging and traceability.

Writes hldspec_event_log.jsonl to the sync directory.
Each entry is one JSON line.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HldspecEvent:
    event_id: str
    timestamp: float
    machine: str
    from_state: str
    to_state: str
    event: str
    inputs: list[str] = field(default_factory=list)    # artifact names read
    outputs: list[str] = field(default_factory=list)   # artifact names written
    decision: str = ""
    notes: str = ""


def append_event(log_path: Path, event: HldspecEvent) -> None:
    """Append one event to the JSONL log. Creates file if missing."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event)) + "\n")


def read_events(log_path: Path) -> list[HldspecEvent]:
    """Read all events from a JSONL log. Returns empty list if file missing."""
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                data = json.loads(line)
                events.append(HldspecEvent(**{k: data[k] for k in HldspecEvent.__dataclass_fields__ if k in data}))
            except (json.JSONDecodeError, TypeError):
                continue
    return events


def make_event_id(machine: str, from_state: str) -> str:
    """Generate a deterministic-ish event ID."""
    ts = int(time.time() * 1000)
    return f"{machine}-{from_state}-{ts}"
