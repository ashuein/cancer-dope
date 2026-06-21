"""Nextflow workflow launch service."""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.config.settings import settings
from backend.services.storage import ensure_run_dirs, run_artifacts_dir, run_dir


@dataclass(frozen=True)
class WorkflowCommand:
    """Prepared workflow command metadata."""

    command: list[str]
    cwd: str
    workflow_path: str
    work_dir: str
    output_dir: str
    dry_run: bool


@dataclass(frozen=True)
class WorkflowLaunchResult:
    """Result of preparing or launching a workflow command."""

    command: WorkflowCommand
    launched: bool
    pid: int | None = None


class WorkflowRunnerService:
    """Build and launch Nextflow commands for case analysis runs.

    The service is deliberately small and framework-independent so API tests can
    exercise command construction with ``dry_run=True`` without requiring a
    Nextflow binary to be installed in the test environment.
    """

    def __init__(
        self,
        nextflow_binary: str | None = None,
        default_workflow_path: Path | None = None,
        launch_cwd: Path | None = None,
        default_work_dir: Path | None = None,
    ) -> None:
        self.nextflow_binary = nextflow_binary or settings.nextflow_binary
        self.default_workflow_path = default_workflow_path or settings.nextflow_workflow_path
        self.launch_cwd = launch_cwd or settings.nextflow_launch_cwd
        self.default_work_dir = default_work_dir or settings.nextflow_work_dir

    def prepare_command(
        self,
        *,
        case_id: int,
        run_id: int,
        workflow_path: Path | None = None,
        work_dir: Path | None = None,
        output_dir: Path | None = None,
        params: dict[str, Any] | None = None,
        profiles: list[str] | None = None,
        revision: str | None = None,
        config_path: Path | None = None,
        resume: bool = False,
        dry_run: bool = True,
    ) -> WorkflowCommand:
        """Build a deterministic Nextflow command for a case run."""
        ensure_run_dirs(case_id, run_id)

        resolved_workflow_path = workflow_path or self.default_workflow_path
        resolved_work_dir = work_dir or self.default_work_dir / f"case-{case_id}" / f"run-{run_id}"
        resolved_output_dir = output_dir or run_artifacts_dir(case_id, run_id)
        resolved_work_dir.mkdir(parents=True, exist_ok=True)
        resolved_output_dir.mkdir(parents=True, exist_ok=True)

        command = [self.nextflow_binary, "run", str(resolved_workflow_path)]
        if revision:
            command.extend(["-r", revision])
        if config_path:
            command.extend(["-c", str(config_path)])
        if profiles:
            command.extend(["-profile", ",".join(profiles)])
        if resume:
            command.append("-resume")
        command.extend(["-work-dir", str(resolved_work_dir)])

        nextflow_params: dict[str, Any] = {
            "case_id": case_id,
            "run_id": run_id,
            "outdir": str(resolved_output_dir),
            "case_dir": str(run_dir(case_id, run_id).parent.parent),
        }
        nextflow_params.update(params or {})
        for name in sorted(nextflow_params):
            value = nextflow_params[name]
            if value is None:
                continue
            command.extend([f"--{name}", self._stringify_param(value)])

        return WorkflowCommand(
            command=command,
            cwd=str(self.launch_cwd),
            workflow_path=str(resolved_workflow_path),
            work_dir=str(resolved_work_dir),
            output_dir=str(resolved_output_dir),
            dry_run=dry_run,
        )

    def launch(
        self,
        *,
        case_id: int,
        run_id: int,
        dry_run: bool = True,
        workflow_path: Path | None = None,
        work_dir: Path | None = None,
        output_dir: Path | None = None,
        params: dict[str, Any] | None = None,
        profiles: list[str] | None = None,
        revision: str | None = None,
        config_path: Path | None = None,
        resume: bool = False,
    ) -> WorkflowLaunchResult:
        """Prepare or start a Nextflow workflow process.

        In dry-run mode, no executable lookup or subprocess spawn occurs.
        """
        command = self.prepare_command(
            case_id=case_id,
            run_id=run_id,
            workflow_path=workflow_path,
            work_dir=work_dir,
            output_dir=output_dir,
            params=params,
            profiles=profiles,
            revision=revision,
            config_path=config_path,
            resume=resume,
            dry_run=dry_run,
        )
        if dry_run:
            return WorkflowLaunchResult(command=command, launched=False)

        if shutil.which(command.command[0]) is None:
            raise FileNotFoundError(f"Nextflow binary not found: {command.command[0]}")

        Path(command.cwd).mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(  # noqa: S603 - command is constructed as an argv list.
            command.command,
            cwd=command.cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return WorkflowLaunchResult(command=command, launched=True, pid=process.pid)

    @staticmethod
    def _stringify_param(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)
