from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = (ROOT / "docs", ROOT / "scripts", ROOT / "tests")
TEXT_EXTS = {".md", ".txt", ".rst", ".py", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".sh"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}

CANONICAL_PATHS = (
    "docs/skeptic_framework_cache.json",
    "docs/skeptic_framework_cache.md",
    "scripts/write_skeptic_cache.py",
    "scripts/run_skeptic_meta_review.py",
)


def _forbidden_cache_paths():
    # Build these dynamically so the test file cannot fail on its own literal strings.
    run = "Run"
    skeptic = "Skeptic"
    framework = "Framework"
    cache = "Cache"
    lower_trigger = (run + skeptic).lower()

    return (
        f"docs/{run}{skeptic}{cache}.json",
        f"docs/{run}{skeptic}{cache}.md",
        f"docs/{run}{skeptic}{framework}{cache}.json",
        f"docs/{run}{skeptic}{framework}{cache}.md",
        f"scripts/write{run}{skeptic}{cache}.py",
        f"scripts/write_{lower_trigger}_cache.py",
        f"scripts/run{run}{skeptic}MetaReview.py",
        f"scripts/run_{lower_trigger}_meta_review.py",
    )


def _iter_repo_text_files():
    for root in SEARCH_ROOTS:
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


def test_canonical_cache_paths_are_documented():
    assert CANONICAL_PATHS == (
        "docs/skeptic_framework_cache.json",
        "docs/skeptic_framework_cache.md",
        "scripts/write_skeptic_cache.py",
        "scripts/run_skeptic_meta_review.py",
    )


def test_no_forbidden_camel_case_or_trigger_cache_paths():
    violations = []
    forbidden_paths = _forbidden_cache_paths()
    for path in _iter_repo_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in forbidden_paths:
            if forbidden in text:
                violations.append(f"{path.relative_to(ROOT)} contains forbidden path {forbidden!r}")

    assert not violations, "Forbidden RunSkeptic cache file paths found:\n" + "\n".join(violations)
