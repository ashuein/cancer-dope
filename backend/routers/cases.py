"""Case and AnalysisRun CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.repositories import (
    ArtifactRepository,
    CaseRepository,
    RunRepository,
    StepRunRepository,
)
from backend.models.schemas import (
    ArtifactResponse,
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    RunCreate,
    RunResponse,
    RunUpdate,
    StepRunResponse,
)

router = APIRouter(prefix="/cases", tags=["cases"])


# ---------- Cases ----------


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(body: CaseCreate, db: AsyncSession = Depends(get_db)):
    repo = CaseRepository(db)
    return await repo.create(label=body.label, metadata_json=body.metadata_json)


@router.get("", response_model=list[CaseResponse])
async def list_cases(db: AsyncSession = Depends(get_db)):
    repo = CaseRepository(db)
    return await repo.list_all()


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    repo = CaseRepository(db)
    case = await repo.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(case_id: int, body: CaseUpdate, db: AsyncSession = Depends(get_db)):
    repo = CaseRepository(db)
    if not body.model_fields_set:
        raise HTTPException(status_code=400, detail="No fields to update")
    case = await repo.update(case_id, label=body.label, metadata_json=body.metadata_json)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.delete("/{case_id}", status_code=204)
async def delete_case(case_id: int, db: AsyncSession = Depends(get_db)):
    repo = CaseRepository(db)
    deleted = await repo.delete(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")


# ---------- Runs ----------


@router.post("/{case_id}/runs", response_model=RunResponse, status_code=201)
async def create_run(case_id: int, body: RunCreate, db: AsyncSession = Depends(get_db)):
    case_repo = CaseRepository(db)
    if not await case_repo.get(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    run_repo = RunRepository(db)
    return await run_repo.create(case_id=case_id, config_snapshot=body.config_snapshot)


@router.get("/{case_id}/runs", response_model=list[RunResponse])
async def list_runs(case_id: int, db: AsyncSession = Depends(get_db)):
    repo = RunRepository(db)
    return await repo.list_by_case(case_id)


@router.get("/{case_id}/runs/{run_id}", response_model=RunResponse)
async def get_run(case_id: int, run_id: int, db: AsyncSession = Depends(get_db)):
    repo = RunRepository(db)
    run = await repo.get(run_id, case_id=case_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.patch("/{case_id}/runs/{run_id}", response_model=RunResponse)
async def update_run(
    case_id: int, run_id: int, body: RunUpdate, db: AsyncSession = Depends(get_db)
):
    repo = RunRepository(db)
    run = await repo.get(run_id, case_id=case_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not body.model_fields_set:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = await repo.update(
        run_id, status=body.status, config_snapshot=body.config_snapshot
    )
    return updated


@router.delete("/{case_id}/runs/{run_id}", status_code=204)
async def delete_run(case_id: int, run_id: int, db: AsyncSession = Depends(get_db)):
    repo = RunRepository(db)
    run = await repo.get(run_id, case_id=case_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await repo.delete(run_id)


# ---------- Steps & Artifacts (read-only) ----------


@router.get("/{case_id}/runs/{run_id}/steps", response_model=list[StepRunResponse])
async def list_steps(case_id: int, run_id: int, db: AsyncSession = Depends(get_db)):
    run_repo = RunRepository(db)
    if not await run_repo.get(run_id, case_id=case_id):
        raise HTTPException(status_code=404, detail="Run not found")
    step_repo = StepRunRepository(db)
    return await step_repo.list_by_run(run_id)


@router.get("/{case_id}/artifacts", response_model=list[ArtifactResponse])
async def list_case_artifacts(case_id: int, db: AsyncSession = Depends(get_db)):
    repo = ArtifactRepository(db)
    return await repo.list_by_case(case_id)
