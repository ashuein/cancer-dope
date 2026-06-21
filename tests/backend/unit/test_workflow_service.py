"""Tests for Nextflow workflow command construction."""

from pathlib import Path

from backend.services.workflow import WorkflowRunnerService


def test_prepare_command_dry_run_builds_nextflow_metadata(tmp_path: Path):
    service = WorkflowRunnerService(
        nextflow_binary="nextflow-test",
        default_workflow_path=tmp_path / "main.nf",
        launch_cwd=tmp_path,
        default_work_dir=tmp_path / "work",
    )

    result = service.launch(
        case_id=7,
        run_id=11,
        dry_run=True,
        params={"sample_sheet": "/inputs/samples.csv", "use_cache": True, "skip_none": None},
        profiles=["docker", "test"],
        revision="v1.2.3",
        resume=True,
    )

    assert result.launched is False
    assert result.pid is None
    command = result.command.command
    assert command[:3] == ["nextflow-test", "run", str(tmp_path / "main.nf")]
    assert ["-profile", "docker,test"] == command[command.index("-profile") : command.index("-profile") + 2]
    assert ["-r", "v1.2.3"] == command[command.index("-r") : command.index("-r") + 2]
    assert "-resume" in command
    assert "--case_id" in command
    assert command[command.index("--case_id") + 1] == "7"
    assert "--run_id" in command
    assert command[command.index("--run_id") + 1] == "11"
    assert "--sample_sheet" in command
    assert command[command.index("--sample_sheet") + 1] == "/inputs/samples.csv"
    assert "--use_cache" in command
    assert command[command.index("--use_cache") + 1] == "true"
    assert "--skip_none" not in command
    assert result.command.cwd == str(tmp_path)
    assert result.command.dry_run is True


def test_launch_dry_run_does_not_require_nextflow_binary(tmp_path: Path):
    service = WorkflowRunnerService(
        nextflow_binary="definitely-not-installed-nextflow",
        default_workflow_path=tmp_path / "main.nf",
        launch_cwd=tmp_path,
        default_work_dir=tmp_path / "work",
    )

    result = service.launch(case_id=1, run_id=2, dry_run=True)

    assert result.launched is False
    assert result.command.command[0] == "definitely-not-installed-nextflow"
