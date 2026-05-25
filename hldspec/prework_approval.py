from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


APPROVAL_SCHEMA_VERSION = 1
APPROVAL_STATUSES = {"APPROVED", "NOT_APPROVED"}


@dataclass(frozen=True)
class PreworkApprovalRecord:
    status: str
    decision: str
    actor: str
    notes: str
    prework_package: str
    warnings: list[str] = field(default_factory=list)
    schema_version: int = APPROVAL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "decision": self.decision,
            "actor": self.actor,
            "notes": self.notes,
            "warnings": list(self.warnings),
            "prework_package": self.prework_package,
        }


def build_prework_approval_record(
    *,
    decision: str,
    actor: str,
    notes: str,
    prework_package: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    if actor != "human":
        warnings.append(
            f"actor='{actor}': gate was not exercised by a human. "
            "This approval may not reflect real human judgment. "
            "Re-run with --actor human after explicit human review."
        )

    record = PreworkApprovalRecord(
        status="APPROVED" if decision == "APPROVE_PLAN" else "NOT_APPROVED",
        decision=decision,
        actor=actor,
        notes=notes,
        warnings=warnings,
        prework_package=prework_package,
    ).to_dict()
    violations = validate_prework_approval_record(record)
    if violations:
        raise ValueError("invalid prework approval record: " + "; ".join(violations))
    return record


def validate_prework_approval_record(record: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    required = [
        "schema_version",
        "status",
        "decision",
        "actor",
        "notes",
        "warnings",
        "prework_package",
    ]
    for field_name in required:
        if field_name not in record:
            violations.append(f"missing required field '{field_name}'")

    if record.get("schema_version") != APPROVAL_SCHEMA_VERSION:
        violations.append(f"schema_version must be {APPROVAL_SCHEMA_VERSION}")

    status = record.get("status")
    if status not in APPROVAL_STATUSES:
        violations.append("status must be APPROVED or NOT_APPROVED")

    if not isinstance(record.get("decision"), str) or not record.get("decision"):
        violations.append("decision must be a non-empty string")

    if not isinstance(record.get("actor"), str) or not record.get("actor"):
        violations.append("actor must be a non-empty string")

    if not isinstance(record.get("notes"), str):
        violations.append("notes must be a string")

    if not isinstance(record.get("warnings"), list) or not all(isinstance(w, str) for w in record.get("warnings", [])):
        violations.append("warnings must be a list of strings")

    if not isinstance(record.get("prework_package"), str) or not record.get("prework_package"):
        violations.append("prework_package must be a non-empty string")

    return violations
