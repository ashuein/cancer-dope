"""Workflow launch endpoints."""

import json
from pathlib import Path
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import AnalysisRun
from backend.db.repositories import CaseRepository, RunRepository
from backend.models.schemas import RunResponse, WorkflowLaunchRequest, WorkflowLaunchResponse
from backend.services.workflow import WorkflowRunnerService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/cases/{case_id}/runs", response_model=WorkflowLaunchResponse, status_code=201)
async def launch_case_workflow(
    case_id: int,
    body: WorkflowLaunchRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowLaunchResponse:
    """Create an analysis run and prepare or launch its Nextflow workflow."""
    case_repo = CaseRepository(db)
    if not await case_repo.get(case_id):
        raise HTTPException(status_code=404, detail="Case not found")

    run_repo = RunRepository(db)
    config_snapshot = json.dumps(body.model_dump(mode="json"), sort_keys=True)
    run = await run_repo.create(case_id=case_id, config_snapshot=config_snapshot)
    run_id = cast(int, run.id)

    service = WorkflowRunnerService()
    try:
        result = service.launch(
            case_id=case_id,
            run_id=run_id,
            dry_run=body.dry_run,
            workflow_path=Path(body.workflow_path) if body.workflow_path else None,
            work_dir=Path(body.work_dir) if body.work_dir else None,
            output_dir=Path(body.output_dir) if body.output_dir else None,
            params=body.params,
            profiles=body.profiles,
            revision=body.revision,
            config_path=Path(body.config_path) if body.config_path else None,
            resume=body.resume,
        )
    except FileNotFoundError as exc:
        await run_repo.update(run_id, status="failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if result.launched:
        updated_run = await run_repo.update(run_id, status="running")
    else:
        updated_run = await run_repo.get(run_id)
    run = cast(AnalysisRun, updated_run)

    return WorkflowLaunchResponse(
        run=RunResponse.model_validate(run),
        dry_run=body.dry_run,
        launched=result.launched,
        pid=result.pid,
        command=result.command.command,
        cwd=result.command.cwd,
        workflow_path=result.command.workflow_path,
        work_dir=result.command.work_dir,
        output_dir=result.command.output_dir,
    )
