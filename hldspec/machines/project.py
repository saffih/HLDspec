from __future__ import annotations

from hldspec.machines.raw_hld_conversion import RawHldConversionMachine
from hldspec.state_machine import (
    MachineContext,
    MachineResult,
    MachineStatus,
    continue_result,
)


class ProjectMachine:
    """Top-level HLDspec V2 coordinator.

    ProjectMachine owns orchestration between sub-machines.
    It does not own detailed gate/checkpoint policy.

    Current V2 slice:
    - delegate raw/converted HLD state to RawHldConversionMachine
    - preserve checkpoint/status semantics
    - expose a top-level MachineResult contract for the CLI
    """

    name = "ProjectMachine"

    def __init__(self, raw_hld_conversion: RawHldConversionMachine | None = None) -> None:
        self.raw_hld_conversion = raw_hld_conversion or RawHldConversionMachine()

    def run(self, context: MachineContext) -> MachineResult:
        raw_result = self.raw_hld_conversion.run(context)

        if raw_result.status in {
            MachineStatus.STOP_CHECKPOINT,
            MachineStatus.BLOCKED,
            MachineStatus.ERROR,
        }:
            return MachineResult(
                machine=self.name,
                state=raw_result.state,
                status=raw_result.status,
                checkpoint=raw_result.checkpoint,
                actions_run=(f"{raw_result.machine}:{raw_result.status.value}", *raw_result.actions_run),
                artifacts_written=raw_result.artifacts_written,
                errors=raw_result.errors,
            )

        if raw_result.status == MachineStatus.CONTINUE:
            return continue_result(
                machine=self.name,
                state="RAW_HLD_CONVERSION_READY_TO_APPLY",
                actions_run=(f"{raw_result.machine}:{raw_result.state}", *raw_result.actions_run),
                artifacts_written=raw_result.artifacts_written,
            )

        if raw_result.status == MachineStatus.DONE:
            return continue_result(
                machine=self.name,
                state="RAW_HLD_CONVERSION_COMPLETE",
                actions_run=(f"{raw_result.machine}:{raw_result.state}", *raw_result.actions_run),
                artifacts_written=raw_result.artifacts_written,
            )

        return MachineResult(
            machine=self.name,
            state="UNKNOWN",
            status=MachineStatus.ERROR,
            errors=(f"Unhandled sub-machine status: {raw_result.status.value}",),
        )
