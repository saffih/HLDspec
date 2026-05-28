"""SpecKit workspace/init boundary.

Plans, validates, and optionally executes the initial SpecKit workspace bootstrap.
HLDspec authors only its own control artifacts under ``.hldspec/source_package/``;
the actual ``.specify/`` tree must come from a real SpecKit init command or an
already valid SpecKit workspace.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


SPEC_KIT_UVX_SOURCE = "git+https://github.com/github/spec-kit.git"


@dataclass(frozen=True)
class InitCommand:
    label: str
    argv: tuple[str, ...]
    source: str

    @property
    def display(self) -> str:
        return shlex.join(self.argv)


@dataclass(frozen=True)
class WorkspaceStatus:
    target: str
    specify_dir_exists: bool
    memory_dir_exists: bool
    source_mirror_exists: bool
    initialized: bool
    validation_error: str | None

    def metadata(self) -> dict:
        return {
            "target": self.target,
            "specify_dir_exists": self.specify_dir_exists,
            "memory_dir_exists": self.memory_dir_exists,
            "source_mirror_exists": self.source_mirror_exists,
            "initialized": self.initialized,
            "validation_error": self.validation_error,
        }


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
    workspace_status: WorkspaceStatus | None = None
    skipped_reason: str | None = None

    @property
    def ok(self) -> bool:
        if self.blocker or self.validation_error:
            return False
        if self.initialized:
            return True
        if not self.selected:
            return False
        if not self.execute:
            return True
        return self.executed and self.returncode == 0 and self.initialized

    def metadata(self) -> dict:
        return {
            "selected_command": list(self.selected.argv) if self.selected else None,
            "selected_command_display": self.selected.display if self.selected else None,
            "selected_command_label": self.selected.label if self.selected else None,
            "selected_command_source": self.selected.source if self.selected else None,
            "available_commands": [list(cmd.argv) for cmd in self.available],
            "available_command_displays": [cmd.display for cmd in self.available],
            "available_command_labels": [cmd.label for cmd in self.available],
            "execute_requested": self.execute,
            "executed": self.executed,
            "initialized": self.initialized,
            "blocker": self.blocker,
            "validation_error": self.validation_error,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "skipped_reason": self.skipped_reason,
            "workspace_status": self.workspace_status.metadata() if self.workspace_status else None,
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


def inspect_workspace(target: str | Path) -> WorkspaceStatus:
    target_path = Path(target)
    specify_dir = target_path / ".specify"
    memory_dir = specify_dir / "memory"
    source_mirror = specify_dir / "source"

    specify_exists = specify_dir.is_dir()
    memory_exists = memory_dir.is_dir()
    source_exists = source_mirror.is_dir()

    validation_error: str | None = None
    if not specify_exists:
        validation_error = f"SpecKit init did not create {specify_dir}"
    elif not memory_exists:
        if source_exists:
            validation_error = (
                f"{specify_dir} has no SpecKit layout (missing .specify/memory/); "
                "only the generated .specify/source/ mirror is present"
            )
        else:
            validation_error = f"{specify_dir} has no SpecKit layout (missing .specify/memory/)"

    return WorkspaceStatus(
        target=str(target_path),
        specify_dir_exists=specify_exists,
        memory_dir_exists=memory_exists,
        source_mirror_exists=source_exists,
        initialized=validation_error is None,
        validation_error=validation_error,
    )


def validate_initialized_workspace(target: Path) -> str | None:
    """Confirm ``.specify/`` is a real SpecKit workspace, not HLDspec's mirror.

    A real ``specify init`` creates ``.specify/memory/`` (SpecKit-owned). HLDspec
    only materialises the read-only mirror under ``.specify/source/``, so the
    mirror alone must never be mistaken for an initialized SpecKit workspace.
    """
    return inspect_workspace(target).validation_error


def _select_first(commands: tuple[InitCommand, ...]) -> InitCommand:
    return commands[0]


def plan_or_init_workspace(
    target: str | Path,
    *,
    execute: bool = False,
    which: Callable[[str], str | None] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    command_selector: Callable[[tuple[InitCommand, ...]], InitCommand] | None = None,
) -> InitResult:
    target_path = Path(target)
    status_before = inspect_workspace(target_path)
    available = detect_init_commands(which=which)
    selected = (command_selector or _select_first)(available) if available else None

    # Already initialized is a valid terminal state. Do not require SpecKit to be on
    # PATH just to continue an existing workspace, and do not rerun init on an
    # already initialized target.
    if status_before.initialized:
        return InitResult(
            selected=selected,
            available=available,
            execute=execute,
            executed=False,
            initialized=True,
            workspace_status=status_before,
            skipped_reason="already_initialized",
        )

    if not available:
        return InitResult(
            selected=None,
            available=(),
            execute=execute,
            executed=False,
            initialized=False,
            blocker="No supported SpecKit init command is available and target is not initialized.",
            workspace_status=status_before,
        )

    if not execute:
        return InitResult(
            selected=selected,
            available=available,
            execute=False,
            executed=False,
            initialized=False,
            workspace_status=status_before,
        )

    run = run or subprocess.run
    target_path.mkdir(parents=True, exist_ok=True)
    try:
        completed = run(
            list(selected.argv),
            cwd=target_path,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        status_after = inspect_workspace(target_path)
        return InitResult(
            selected=selected,
            available=available,
            execute=True,
            executed=True,
            initialized=status_after.initialized,
            blocker=f"SpecKit init command failed to start: {exc}",
            validation_error=status_after.validation_error,
            returncode=127,
            stdout="",
            stderr=str(exc),
            workspace_status=status_after,
        )

    status_after = inspect_workspace(target_path)
    return InitResult(
        selected=selected,
        available=available,
        execute=True,
        executed=True,
        initialized=status_after.initialized,
        validation_error=status_after.validation_error,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        workspace_status=status_after,
    )
