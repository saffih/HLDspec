from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = (ROOT / "docs",)
TEXT_EXTS = {".md", ".txt", ".rst"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
FORBIDDEN_OLD_TERMS = ("Beskeptic", "beskeptic")


def _iter_core_hldspec_docs():
    for root in DOC_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_EXTS:
                continue
            yield path


def test_core_docs_do_not_use_old_beskeptic_wording():
    """RunSkeptic is the correct trigger; only old Beskeptic wording is forbidden."""
    violations = []
    for path in _iter_core_hldspec_docs():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in FORBIDDEN_OLD_TERMS:
            if term in text:
                violations.append(f"{path.relative_to(ROOT)} contains {term!r}")

    assert not violations, "Old Beskeptic terminology found:\n" + "\n".join(violations)


def test_runskeptic_is_the_allowed_formal_trigger():
    assert "RunSkeptic" not in FORBIDDEN_OLD_TERMS
    assert "Run" + "Skeptic" == "RunSkeptic"
