from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_agent_first_start_creates_target_session(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    source = tmp_path / "HLD.md"
    target = tmp_path / "target"
    source.write_text("# High-Level Design\n\n## HLD-001 - Purpose\n\nHLD-ID: HLD-001\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "hldspec_agent_session.py"),
            "start",
            "--source",
            str(source),
            "--target",
            str(target),
            "--agent",
            "manual",
            "--comment",
            "test run",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    session_path = target / ".hldspec" / "agent_session.json"
    prompt_path = target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
    assert session_path.exists()
    assert prompt_path.exists()
    assert (target / "targetHLD" / "raw" / "HLD.raw.md").exists()
    assert (target / "targetHLD" / "HLD.md").exists()

    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert session["agent"] == "manual"
    assert session["mode"] == "create"
    assert session["source"]["path"] == str(source.resolve())
    assert "start an agent session" in result.stdout


def test_agent_first_diff_detects_unchanged_source(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    source = tmp_path / "HLD.md"
    target = tmp_path / "target"
    source.write_text("# HLD\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "hldspec_agent_session.py"),
            "start",
            "--source",
            str(source),
            "--target",
            str(target),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "hldspec_agent_session.py"),
            "diff",
            "--source",
            str(source),
            "--target",
            str(target),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Diff status: unchanged" in result.stdout
