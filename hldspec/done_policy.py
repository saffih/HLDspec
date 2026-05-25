"""Done-means-verified policy.

TASKS.md and any task tracker must use these statuses.
'COMPLETE' is only valid when GATE_VERIFIED is also present.
"""
from __future__ import annotations
from enum import Enum


class DoneStatus(str, Enum):
    IMPLEMENTED   = "IMPLEMENTED"   # Code written; tests not yet run
    TESTED        = "TESTED"        # Tests written and passing
    GATE_VERIFIED = "GATE_VERIFIED" # ready-gate / fitness check passed
    RELEASE_READY = "RELEASE_READY" # All of the above; merged to main

    @classmethod
    def is_complete(cls, status: "DoneStatus") -> bool:
        return status in {cls.GATE_VERIFIED, cls.RELEASE_READY}
