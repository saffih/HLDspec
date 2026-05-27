"""SpecKit workspace/init boundary.

Plans and optionally executes the initial SpecKit workspace bootstrap. HLDspec
authors only its own control artifacts under `.hldspec/source_package/`; the
actual `.specify/` tree must come from a real SpecKit init command.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


SPEC_KIT_UVX_SOURCE = "git+https://github.com/github/spec-kit.git"


@dataclass(frozen=True)
class InitCommand:
    label: str
    argv: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class InitResult:
    selected: InitCommand | None
    available: tuple[InitCommand, ...]
    execute: bool
    executed: bool
    initialized: bool
    blocker: str | None = None
    validation_error: str | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        if self.blocker or self.validation_error:
            return False
        if not self.selected:
            return False
        if not self.execute:
            return True
        return self.executed and self.returncode == 0 and self.initialized

    def metadata(self) -> dict:
        return {
            "selected_command": list(self.selected.argv) if self.selected else None,
            "selected_command_label": self.selected.label if self.selected else None,
            "selected_command_source": self.selected.source if self.selected else None,
            "available_commands": [list(cmd.argv) for cmd in self.available],
            "available_command_labels": [cmd.label for cmd in self.available],
            "execute_requested": self.execute,
            "executed": self.executed,
            "initialized": self.initialized,
            "blocker": self.blocker,
            "validation_error": self.validation_error,
            "returncode": self.returncode,
        }


def detect_init_commands(
    which: Callable[[str], str | None] | None = None,
) -> tuple[InitCommand, ...]:
    which = which or shutil.which
    commands: list[InitCommand] = []
    if which("specify"):
        commands.append(
            InitCommand(
                label="specify",
                argv=("specify", "init", "."),
                source="local-binary",
            )
        )
    if which("spec-kit"):
        commands.append(
            InitCommand(
                label="spec-kit",
                argv=("spec-kit", "init", "."),
                source="local-binary",
            )
        )
    if which("uvx"):
        commands.append(
            InitCommand(
                label="uvx-spec-kit",
                argv=(
                    "uvx",
                    "--from",
                    SPEC_KIT_UVX_SOURCE,
                    "spec-kit",
                    "init",
                    ".",
                ),
                source="uvx",
            )
        )
    return tuple(commands)


def validate_initialized_workspace(target: Path) -> str | None:
    specify_dir = target / ".specify"
    if not specify_dir.is_dir():
        return f"SpecKit init did not create {specify_dir}"
    return None


def plan_or_init_workspace(
    target: str | Path,
    *,
    execute: bool = False,
    which: Callable[[str], str | None] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> InitResult:
    target_path = Path(target)
    available = detect_init_commands(which=which)
    if not available:
        return InitResult(
            selected=None,
            available=(),
            execute=execute,
            executed=False,
            initialized=False,
            blocker="No supported SpecKit init command is available.",
        )

    selected = available[0]
    if not execute:
        return InitResult(
            selected=selected,
            available=available,
            execute=False,
            executed=False,
            initialized=(target_path / ".specify").is_dir(),
        )

    run = run or subprocess.run
    target_path.mkdir(parents=True, exist_ok=True)
    completed = run(
        list(selected.argv),
        cwd=target_path,
        text=True,
        capture_output=True,
        check=False,
    )
    validation_error = validate_initialized_workspace(target_path)
    return InitResult(
        selected=selected,
        available=available,
        execute=True,
        executed=True,
        initialized=validation_error is None,
        validation_error=validation_error,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )

