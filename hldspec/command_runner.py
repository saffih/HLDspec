from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    command: tuple[str, ...]
    stdout: str = ""
    stderr: str = ""


class CommandRunner:
    def run(self, command: Sequence[str], *, cwd: Path | None = None, capture: bool = False, input_text: str | None = None) -> CommandResult:
        proc = subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            input=input_text,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=False,
        )
        return CommandResult(
            returncode=proc.returncode,
            command=tuple(str(item) for item in command),
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
