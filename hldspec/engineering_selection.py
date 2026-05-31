"""Minimal Engineering Toolbox selection and guidelines generation.

This is the MVP slice of the Engineering Toolbox enforcement loop: it selects the
P0 cards that apply to a given HLD and renders a real, target-specific
``engineering_guidelines.md`` for the source package.

Scope and honesty:

- The P0 card data is encoded here (we do not parse the whole markdown toolbox;
  ``docs/ENGINEERING_TOOLBOX.md`` remains the human catalog and contract).
- A small baseline set of cards is always selected because nearly every generated
  software project needs them. The rest are trigger-selected from the HLD text.
- This module does NOT implement the full ``selection.json`` / ``decisions.jsonl``
  gate loop. It generates selected guidance only; durable principles are surfaced
  as Constitution Candidates that still require review, and the target
  constitution is never silently overwritten.
"""
from __future__ import annotations

import re

SCHEMA_VERSION = 1

# Cards selected for nearly every project regardless of HLD wording.
BASELINE_CARDS: tuple[str, ...] = (
    "architecture.business_logic_container",
    "testing.design_for_testability",
    "environment.stage_safe_testing",
    "environment.prod_test_separation",
)

# Deterministic output order across all P0 cards (baseline + trigger-selected).
CARD_ORDER: tuple[str, ...] = (
    "architecture.hexagonal_ports_adapters",
    "architecture.business_logic_container",
    "architecture.modular_boundaries",
    "api.http_json",
    "data.schema_discipline",
    "concurrency.optimistic_revision",
    "testing.design_for_testability",
    "testing.business_logic_coverage",
    "testing.contract_boundary",
    "testing.ui_tester_skill",
    "testing.resettable_fixtures",
    "environment.stage_safe_testing",
    "environment.prod_test_separation",
)

# Keyword triggers per trigger-selected card. Matched case-insensitively with word
# boundaries so short tokens ("api", "ui", "cli") do not match inside other words.
TRIGGER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "architecture.hexagonal_ports_adapters": (
        "api", "ui", "cli", "persistence", "database", "external integration",
        "message bus", "queue", "service", "sdk", "filesystem", "integration",
        "business",
    ),
    "api.http_json": (
        "http", "rest", "api", "endpoint", "client", "service boundary", "json",
    ),
    "data.schema_discipline": (
        "database", "persistence", "table", "record", "schema", "migration",
        "entity", "index", "query", "storage",
    ),
    "testing.contract_boundary": (
        "public api", "api", "cli", "ui workflow", "external integration",
        "file format", "event payload", "import", "export", "client boundary",
        "client",
    ),
    "testing.ui_tester_skill": (
        "ui", "web app", "page", "form", "navigation", "layout", "browser",
        "accessibility", "screenshot", "user-visible",
    ),
    "testing.business_logic_coverage": (
        "business rule", "business rules", "workflow", "validation",
        "state transition", "permission", "pricing", "scheduling", "domain",
        "decision", "policy",
    ),
    "testing.resettable_fixtures": (
        "persistent state", "ui flow", "e2e", "external service",
        "generated file", "seeded data", "import", "export", "fixture",
    ),
    "concurrency.optimistic_revision": (
        "shared mutable", "concurrent edit", "multiple users", "collaboration",
        "revision", "versioning", "conflict", "simultaneous update",
    ),
    "architecture.modular_boundaries": (
        "module", "modules", "domain", "bounded context", "multiple actors",
        "feature", "ownership", "future change",
    ),
}

# Encoded P0 card content (condensed from docs/ENGINEERING_TOOLBOX.md, kept real).
CARDS: dict[str, dict] = {
    "architecture.hexagonal_ports_adapters": {
        "trigger": "API, CLI, UI, persistence, external integration, replaceable infrastructure, or meaningful business behavior exists.",
        "default_choice": "Use hexagonal architecture / ports and adapters; domain and application code define core behavior and ports; HTTP, CLI, UI, database, filesystem, queues, clocks, IDs, and external SDKs are adapters.",
        "architecture": [
            "business logic does not depend on frameworks, transports, or infrastructure",
            "ports/interfaces describe what the core needs",
            "adapters translate external concerns into core calls",
        ],
        "tests": [
            "core behavior tests through the business logic container and ports",
            "adapter tests for each real boundary",
            "contract tests where external/client boundaries exist",
        ],
        "forbidden": [
            "placing business rules in controllers, handlers, UI components, DB adapters, or SDK wrappers",
            "letting external tools shape the domain model",
            "requiring a server/UI/database to test core rules",
        ],
        "evidence": [
            "visible core/application boundary",
            "tests proving core behavior without production services",
            "adapter tests or contracts",
        ],
        "constitution_candidate": "yes",
        "preferred_choice": True,
    },
    "architecture.business_logic_container": {
        "trigger": "business rules, workflows, decisions, validation, state transitions, permissions, pricing, scheduling, or domain behavior.",
        "default_choice": "Put business logic in a fully testable business logic container (application service, use-case layer, domain service, or domain model); handlers, CLI, UI, jobs, and DB adapters call into it.",
        "architecture": [
            "one clear entry point per use case/workflow",
            "injected dependencies/ports for time, IDs, persistence, external APIs, filesystem, network, randomness",
            "no dependency on production services for focused behavior tests",
        ],
        "tests": [
            "focused business logic tests for every business rule",
            "negative/edge-case tests",
            "regression tests for prior bugs or risky paths",
        ],
        "forbidden": [
            "testing business rules only through UI or HTTP smoke tests",
            "hiding use-case logic in framework callbacks",
            "using real production state in focused tests",
        ],
        "evidence": [
            "business logic container exists",
            "focused tests cover rules, errors, and edge cases",
        ],
        "constitution_candidate": "yes",
        "preferred_choice": True,
    },
    "architecture.modular_boundaries": {
        "trigger": "multiple domains, features, actors, bounded contexts, or likely future change pressure.",
        "default_choice": "Prefer modular monolith/internal modules before services unless deployment, scaling, ownership, security, or runtime isolation boundaries are real; each module declares ownership, inputs, outputs, contracts, and persistence boundary.",
        "architecture": [
            "clear module boundaries",
            "no accidental cross-module data ownership",
            "interfaces/contracts for important cross-module calls",
        ],
        "tests": [
            "module-level behavior tests",
            "contract tests for cross-module boundaries when needed",
        ],
        "forbidden": [
            "splitting into services only for style",
            "direct database sharing across ownership boundaries without explicit reason",
            "circular module dependencies",
        ],
        "evidence": [
            "module boundary description",
            "tests or contracts for cross-boundary behavior",
        ],
        "constitution_candidate": "no, unless the target needs long-lived modularity law",
        "preferred_choice": True,
    },
    "api.http_json": {
        "trigger": "an HTTP API, client boundary, public API, multi-client API, or service boundary exists.",
        "default_choice": "Default to simple HTTP + JSON with explicit DTOs/contracts and a small endpoint surface; use OpenAPI/JSON Schema for client/multi-client/public APIs; do not default to hypermedia/HATEOAS.",
        "architecture": [
            "HTTP handlers translate transport concerns and call the business logic container",
            "DTOs/contracts live at the boundary",
            "domain/application behavior does not live in handlers",
        ],
        "tests": [
            "handler/contract tests for boundary shape",
            "business logic tests below the HTTP layer",
            "negative tests for invalid input and errors",
        ],
        "forbidden": [
            "hiding business rules in handlers",
            "accepting untyped/raw payloads as domain objects",
            "using endpoint tests as the only proof of business behavior",
        ],
        "evidence": [
            "contract files or explicit DTOs",
            "focused tests proving validation and business behavior",
        ],
        "constitution_candidate": "yes, as explicit contracts at system boundaries",
        "preferred_choice": True,
    },
    "data.schema_discipline": {
        "trigger": "persistent entities, migrations, indexes, uniqueness, joins, or business records exist.",
        "default_choice": "Use stable primary keys, foreign keys where DB-enforced integrity matters, unique constraints for business uniqueness, and indexes only for named query paths; use JSON columns only for truly flexible data and promote queried/business-critical fields to typed schema.",
        "architecture": [
            "persistence concerns stay behind repositories/adapters/ports",
            "schema choices documented as selected guidance or decisions",
        ],
        "tests": [
            "persistence integration tests on disposable test DBs or fixtures",
            "uniqueness and integrity negative tests",
            "migration smoke where migrations exist",
        ],
        "forbidden": [
            "storing core typed business data as opaque JSON for speed",
            "running schema-changing tests against production or user-owned data",
            "adding indexes without named query evidence",
        ],
        "evidence": [
            "schema/migration file",
            "tests or migration smoke output",
            "reason for non-obvious schema choices",
        ],
        "constitution_candidate": "yes, as source-of-truth and data integrity must be explicit",
        "preferred_choice": True,
    },
    "concurrency.optimistic_revision": {
        "trigger": "shared mutable records can be edited by more than one actor, process, request, agent, or UI session.",
        "default_choice": "Default to optimistic revision updates (UPDATE ... SET revision = revision + 1 WHERE id = ? AND revision = ?); affected rows 0 means conflict/reload/merge/retry per a declared policy; do not default to broad locking.",
        "architecture": [
            "revision/version field or equivalent conflict token",
            "explicit conflict handling path",
            "business logic container owns conflict semantics",
        ],
        "tests": [
            "two actors reading the same revision",
            "first update succeeds",
            "stale second update fails or resolves per policy",
            "no silent overwrite",
        ],
        "forbidden": [
            "last-write-wins without an explicit product decision",
            "hidden broad locks as a default",
            "conflict policy only in UI with no domain/application test",
        ],
        "evidence": [
            "revision update code",
            "stale-write focused test",
            "phase report naming the conflict policy",
        ],
        "constitution_candidate": "no, except as part of source-of-truth integrity",
        "preferred_choice": True,
    },
    "testing.design_for_testability": {
        "trigger": "any product surface exists — business logic, CLI, API, persistence, or user-visible UI; this card is always selected because every product must be fully tested.",
        "default_choice": "Every product surface must be fully tested: business logic, CLI, API, persistence, and user-visible UI each require tests that execute and pass before the work is considered done — a specified-but-unrun test is not coverage. Design for testability from the start; time, IDs, randomness, external APIs, filesystem, network, queues, and production services must be injectable/replaceable. UI and browser surfaces require a UI/e2e harness (e.g. a UI tester skill). If no test harness exists for a surface, the slice must create the approved harness or block for explicit human approval (waiver-by-exception) — it must NOT silently ship that surface untested.",
        "architecture": [
            "business logic container accepts ports/dependencies",
            "adapters replaceable with fakes/stubs/test doubles",
            "configuration separates test/stage/prod",
            "each product surface has a reachable, runnable test seam",
        ],
        "tests": [
            "focused unit/application tests without production dependencies",
            "integration tests where boundary behavior requires them",
            "executed-and-green tests for every product surface, UI/browser included",
            "deterministic tests for time/ID/randomness-sensitive logic",
        ],
        "forbidden": [
            "using production config in tests",
            "treating a specified-but-unrun test plan as 'tested'",
            "shipping any product surface (including UI/browser) with no executed test and no approved waiver",
            "tests that pass only by depending on real time, network, or production data",
        ],
        "evidence": [
            "injectable dependency seams",
            "per-surface executed-and-green test output (UI/browser included)",
            "approved waiver recorded for any surface with no available harness",
            "explicit test/stage config",
        ],
        "constitution_candidate": "yes",
        "preferred_choice": True,
    },
    "testing.business_logic_coverage": {
        "trigger": "business rules, workflows, domain decisions, state transitions, permissions, pricing, scheduling, validation, or risk-bearing logic exists.",
        "default_choice": "Every business rule must have focused unit/domain/application tests; handler/UI/E2E tests are not a substitute.",
        "architecture": [
            "business logic callable directly below transport/UI",
            "rule inputs and outputs observable in tests",
        ],
        "tests": [
            "positive case",
            "negative case",
            "edge case",
            "stale/regression case when relevant",
        ],
        "forbidden": [
            "relying only on UI automation or manual QA for domain behavior",
            "adding logic without tests because it is small",
            "testing only happy paths",
        ],
        "evidence": [
            "focused test names or report entries tied to rules",
        ],
        "constitution_candidate": "yes",
        "preferred_choice": True,
    },
    "testing.contract_boundary": {
        "trigger": "public API, CLI, UI workflow, external integration, file format, event payload, data import/export, or client boundary exists.",
        "default_choice": "Cover boundary behavior with contract tests, golden tests, schema checks, or stable fixtures.",
        "architecture": [
            "boundary shape is explicit",
            "payloads/commands/events/errors documented or schema-backed",
        ],
        "tests": [
            "valid contract example",
            "invalid contract example",
            "backward compatibility or migration test when relevant",
        ],
        "forbidden": [
            "undocumented payload changes",
            "changing CLI/API/UI-visible behavior without contract/golden update",
            "treating adapter mocks as proof of a public contract",
        ],
        "evidence": [
            "contract/golden/schema test output",
            "changed contract reviewed when behavior changes",
        ],
        "constitution_candidate": "yes, as boundary contract discipline",
        "preferred_choice": True,
    },
    "testing.ui_tester_skill": {
        "trigger": "user-visible UI exists or a feature changes UI behavior, layout, forms, navigation, accessibility, errors, empty states, or regressions.",
        "default_choice": "Use a UI tester skill or equivalent UI validation against test/stage data; verify user-visible flows, errors, empty states, and regressions.",
        "architecture": [
            "UI can point to test/stage backend or fixture data",
            "UI test setup does not mutate production/user-owned data",
            "business logic remains testable below UI",
        ],
        "tests": [
            "happy path",
            "error path",
            "empty/loading state where relevant",
            "regression/golden/screenshot/accessibility check where relevant",
        ],
        "forbidden": [
            "claiming UI is tested because backend tests pass",
            "running UI automation against production/user-owned data",
            "embedding business rules only in UI components",
        ],
        "evidence": [
            "UI tester report or command output",
            "environment used",
            "data safety statement",
        ],
        "constitution_candidate": "no, unless UI safety is a permanent project rule",
        "preferred_choice": True,
    },
    "testing.resettable_fixtures": {
        "trigger": "tests use persistent state, UI flows, e2e flows, external services, generated files, or seeded data.",
        "default_choice": "Tests need a deterministic seed/reset strategy; E2E and UI tests must clean up or use isolated disposable state.",
        "architecture": [
            "fixture seed and cleanup entry points",
            "test data namespacing or disposable resources",
            "no dependency on execution order",
        ],
        "tests": [
            "repeated run passes",
            "cleanup/reset works",
            "test data does not leak into production/user data",
        ],
        "forbidden": [
            "manual fixture cleanup",
            "order-dependent tests",
            "shared mutable test state without reset",
        ],
        "evidence": [
            "seed/reset command or fixture code",
            "repeated-run result or cleanup statement",
        ],
        "constitution_candidate": "no",
        "preferred_choice": True,
    },
    "environment.stage_safe_testing": {
        "trigger": "feature work can write, delete, migrate, seed, import, export, automate UI, call external systems, or otherwise mutate state.",
        "default_choice": "Feature work must not corrupt the user's active product or data; run implementation and tests in an isolated test/stage workspace; production or user-owned data requires explicit approval before mutation.",
        "architecture": [
            "clear test/stage/prod labels",
            "safe test/stage environment boundaries",
            "disposable workspace, temp dir, test DB, seeded fixtures, or isolated service",
            "safe cleanup/reset path",
        ],
        "tests": [
            "smoke proves generated artifacts stay under the target/temp root when applicable",
            "destructive flows use disposable state",
            "migration tests use a test DB or explicit dry-run",
        ],
        "forbidden": [
            "running migrations/deletes/seeds/UI automation against production by default",
            "using the user's active workspace as a destructive test target",
            "hiding environment assumptions in shell history or local config",
        ],
        "evidence": [
            "environment name",
            "target path",
            "reset/cleanup method",
            "explicit approval when touching production or user-owned data",
        ],
        "constitution_candidate": "yes",
        "preferred_choice": True,
    },
    "environment.prod_test_separation": {
        "trigger": "any persistent data, external service, deployment environment, UI automation, migration, destructive operation, or user-owned workspace exists.",
        "default_choice": "Separate test, stage, and production data/config; destructive tests require throwaway targets, temp dirs, test DBs, mocked external services, or seeded fixtures; no feature agent runs migrations/deletes/writes/imports/exports/UI automation against production unless explicitly approved.",
        "architecture": [
            "environment-specific config",
            "no shared production credentials in the test workflow",
            "test/stage data isolation",
        ],
        "tests": [
            "environment guard test or dry-run check where possible",
            "smoke showing test target isolation for generated artifacts",
            "reset path for fixtures/state",
        ],
        "forbidden": [
            "defaulting to production config",
            "using real customer/user data in automation",
            "running destructive tests without a reset strategy",
        ],
        "evidence": [
            "environment labels in reports",
            "commands or config proving the test/stage target",
            "approval evidence for any production mutation",
        ],
        "constitution_candidate": "yes",
        "preferred_choice": True,
    },
}

# Markers that prove the generated guidelines are real selected guidance.
REQUIRED_GUIDELINE_MARKERS: tuple[str, ...] = (
    "# Engineering Guidelines",
    "generated by HLDspec",
    "Required architecture shape",
    "Required tests",
    "Forbidden shortcuts",
    "Evidence required",
    "Constitution candidate",
    "Preferred choice",
    "selected guidance, not a full toolbox dump",
    "Do not silently overwrite the target constitution",
) + BASELINE_CARDS


def _mentions(text: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}\b", text, flags=re.IGNORECASE) is not None


def _matched_keywords(text: str, keywords: tuple[str, ...]) -> list[str]:
    return [kw for kw in keywords if _mentions(text, kw)]


def detect_engineering_triggers(hld_text: str) -> dict[str, bool]:
    """Map each P0 card to whether it is selected for this HLD.

    Baseline cards are always True. Trigger-selected cards are True when their
    keywords appear in the HLD (case-insensitive, word-boundary matched).
    """
    triggers: dict[str, bool] = {}
    for card_id in CARD_ORDER:
        if card_id in BASELINE_CARDS:
            triggers[card_id] = True
        else:
            triggers[card_id] = bool(_matched_keywords(hld_text, TRIGGER_KEYWORDS[card_id]))
    return triggers


def select_p0_cards(hld_text: str) -> list[dict]:
    """Return the selected P0 card records, in canonical order, with evidence."""
    triggers = detect_engineering_triggers(hld_text)
    selected: list[dict] = []
    for card_id in CARD_ORDER:
        if not triggers[card_id]:
            continue
        card = dict(CARDS[card_id])
        card["id"] = card_id
        if card_id in BASELINE_CARDS:
            card["triggered_by"] = ["baseline (always selected)"]
        else:
            card["triggered_by"] = _matched_keywords(hld_text, TRIGGER_KEYWORDS[card_id])
        selected.append(card)
    return selected


def _is_constitution_candidate(value: str) -> bool:
    return str(value).strip().lower().startswith("yes")


def render_engineering_guidelines_md(hld_text: str, *, project_name: str = "") -> str:
    """Render the target-specific engineering_guidelines.md from selected P0 cards."""
    cards = select_p0_cards(hld_text)

    lines: list[str] = [
        "# Engineering Guidelines",
        "",
        "Status: generated by HLDspec (minimal P0-card selection).",
        "",
        f"Project/target context: {project_name or 'unspecified'}",
        "",
        "This is selected guidance, not a full toolbox dump. HLDspec selects only the",
        "P0 cards triggered by this HLD plus the always-on baseline cards.",
        "Do not silently overwrite the target constitution; durable principles are",
        "proposed as Constitution Candidates and require review before becoming law.",
        "",
        "## Selected cards summary",
        "",
    ]
    lines += [f"- {card['id']} — {', '.join(card['triggered_by'])}" for card in cards]
    lines.append("")

    for card in cards:
        lines += [
            f"## {card['id']}",
            "",
            f"Trigger evidence: {', '.join(card['triggered_by'])}",
            f"Trigger: {card['trigger']}",
            f"Default choice: {card['default_choice']}",
            "",
            "Required architecture shape:",
            *[f"- {item}" for item in card["architecture"]],
            "",
            "Required tests:",
            *[f"- {item}" for item in card["tests"]],
            "",
            "Forbidden shortcuts:",
            *[f"- {item}" for item in card["forbidden"]],
            "",
            "Evidence required:",
            *[f"- {item}" for item in card["evidence"]],
            "",
            f"Constitution candidate: {card['constitution_candidate']}",
            f"Preferred choice: {'yes' if card['preferred_choice'] else 'no'}",
            "",
        ]

    candidate_ids = [c["id"] for c in cards if _is_constitution_candidate(c["constitution_candidate"])]
    lines += [
        "## Constitution candidates",
        "",
        "Durable engineering principles proposed for the target SpecKit constitution",
        "after review. HLDspec proposes; it does not apply these automatically.",
        "",
    ]
    lines += [f"- {cid}" for cid in candidate_ids] or ["- none selected"]
    lines += [
        "",
        "## Preferred choice selections",
        "",
        "Context-specific defaults for SpecKit and implementation agents. These are",
        "practical defaults, not permanent law.",
        "",
    ]
    lines += [f"- {c['id']}: {c['default_choice']}" for c in cards if c["preferred_choice"]]
    lines += [
        "",
        "## Stage-safe testing and prod/test separation warning",
        "",
        "Feature work must not corrupt the user's active product or data.",
        "Run implementation and tests in an isolated test/stage workspace.",
        "Test, stage, and production data/config must be separated.",
        "Production or user-owned data requires explicit approval before mutation.",
        "",
    ]
    return "\n".join(lines) + "\n"


def validate_engineering_guidelines(text: str) -> list[str]:
    """Return a list of missing required markers (empty means the content is real)."""
    return [f"missing required marker: {marker}" for marker in REQUIRED_GUIDELINE_MARKERS if marker not in text]
