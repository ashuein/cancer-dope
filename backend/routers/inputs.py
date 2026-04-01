"""Input registration and validation endpoints.

Routes:
    POST /cases/{case_id}/inputs/upload   — upload a file
    POST /cases/{case_id}/inputs/register — register from existing paths (copies into managed storage)
    GET  /cases/{case_id}/inputs/summary  — normalized input summary with module readiness
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.db.database import get_db
from backend.db.models import ArtifactStatus
from backend.db.repositories import ArtifactRepository, CaseRepository, RunRepository, StepRunRepository
from backend.models.inputs import (
    InputRegistration,
    InputRegistrationBatch,
    InputSummary,
    InputType,
    InputValidationResult,
    MODULE_CAPABILITIES,
    ValidationIssue,
)
from backend.parsers.registry import validate_input
from backend.services.storage import case_inputs_dir, path_checksum, path_size, unique_input_name

router = APIRouter(prefix="/cases/{case_id}/inputs", tags=["inputs"])


async def _get_or_create_input_run(case_id: int, db: AsyncSession):
    """Get existing input-registration run or create one."""
    run_repo = RunRepository(db)
    runs = await run_repo.list_by_case(case_id)
    for run in runs:
        if '"type": "input_registration"' in (run.config_snapshot or ""):
            return run
    return await run_repo.create(case_id, config_snapshot='{"type": "input_registration"}')


@router.post("/upload", response_model=InputValidationResult)
async def upload_input(
    case_id: int,
    input_type: InputType,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and register it as a case input."""
    case = await CaseRepository(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    inputs_dir = case_inputs_dir(case_id)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    # Use a UUID temp name to avoid collisions between concurrent uploads
    temp_name = f"_tmp_{uuid.uuid4().hex}_{file.filename}"
    temp_dest = inputs_dir / temp_name
    with open(temp_dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    result = validate_input(temp_dest, input_type)

    if result.valid:
        run = await _get_or_create_input_run(case_id, db)

        step_repo = StepRunRepository(db)
        step = await step_repo.create(run.id, module="input", step_name=f"register_{input_type.value}")
        final_dest = inputs_dir / unique_input_name(file.filename, step.id)

        try:
            temp_dest.rename(final_dest)

            checksum = path_checksum(final_dest)
            size = path_size(final_dest)
            await step_repo.mark_completed(step.id)

            art_repo = ArtifactRepository(db)
            await art_repo.create(
                step_run_id=step.id,
                artifact_type=f"input_{input_type.value}",
                fmt=final_dest.suffix.lstrip(".") or "bin",
                path=str(final_dest),
                checksum=checksum,
                size_bytes=size,
                status=ArtifactStatus.READY,
            )
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            await step_repo.mark_failed(step.id, error_msg)
            temp_dest.unlink(missing_ok=True)
            if final_dest.is_file():
                final_dest.unlink(missing_ok=True)
            # Report failure to the client — validation passed but registration failed
            result.valid = False
            result.issues.append(ValidationIssue(
                field="registration", message=f"Registration failed: {error_msg}", severity="error",
            ))
    else:
        temp_dest.unlink(missing_ok=True)

    return result


@router.post("/register", response_model=list[InputValidationResult])
async def register_inputs(
    case_id: int,
    body: InputRegistrationBatch,
    db: AsyncSession = Depends(get_db),
):
    """Register inputs from existing paths — copies into managed case storage."""
    case = await CaseRepository(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    results: list[InputValidationResult] = []
    run = await _get_or_create_input_run(case_id, db)

    inputs_dir = case_inputs_dir(case_id)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    for reg in body.inputs:
        if not reg.path:
            results.append(InputValidationResult(
                input_type=reg.input_type, filename=reg.filename,
                valid=False,
                issues=[ValidationIssue(
                    field="path", message="Path is required for registration", severity="error",
                )],
            ))
            continue

        source = Path(reg.path)
        result = validate_input(source, reg.input_type)
        results.append(result)

        if not result.valid:
            continue

        # Use the caller-provided filename for the managed name, not source.name
        display_name = reg.filename or source.name

        step_repo = StepRunRepository(db)
        step = await step_repo.create(run.id, module="input", step_name=f"register_{reg.input_type.value}")
        managed_name = unique_input_name(display_name, step.id)
        managed_path = inputs_dir / managed_name

        try:
            if source.is_file():
                shutil.copy2(source, managed_path)
                fmt = managed_path.suffix.lstrip(".") or "bin"
            elif source.is_dir():
                shutil.copytree(source, managed_path)
                fmt = "dir"
            else:
                raise FileNotFoundError(f"Source is neither file nor directory: {source}")

            checksum = path_checksum(managed_path)
            size = path_size(managed_path)
            await step_repo.mark_completed(step.id)

            art_repo = ArtifactRepository(db)
            await art_repo.create(
                step_run_id=step.id,
                artifact_type=f"input_{reg.input_type.value}",
                fmt=fmt,
                path=str(managed_path),
                checksum=checksum,
                size_bytes=size,
                status=ArtifactStatus.READY,
            )
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            await step_repo.mark_failed(step.id, error_msg)
            if managed_path.is_file():
                managed_path.unlink(missing_ok=True)
            elif managed_path.is_dir():
                shutil.rmtree(managed_path, ignore_errors=True)
            # Update the result to reflect registration failure
            result.valid = False
            result.issues.append(ValidationIssue(
                field="registration", message=f"Registration failed: {error_msg}", severity="error",
            ))

    return results


@router.get("/summary", response_model=InputSummary)
async def input_summary(
    case_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return a normalized summary of all registered inputs for a case."""
    case = await CaseRepository(db).get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    art_repo = ArtifactRepository(db)
    artifacts = await art_repo.list_by_case(case_id)

    registered_types: list[InputType] = []
    for art in artifacts:
        if art.artifact_type.startswith("input_"):
            type_str = art.artifact_type[len("input_"):]
            try:
                registered_types.append(InputType(type_str))
            except ValueError:
                pass

    module_readiness = _compute_module_readiness(set(registered_types))

    return InputSummary(
        case_id=case_id,
        registered_types=sorted(set(registered_types), key=lambda t: t.value),
        module_readiness=module_readiness,
        file_count=len([a for a in artifacts if a.artifact_type.startswith("input_")]),
    )


def _compute_module_readiness(registered: set[InputType]) -> dict[str, bool]:
    """Compute per-module readiness based on registered input types."""
    readiness: dict[str, bool] = {}
    for cap in MODULE_CAPABILITIES:
        if cap.required:
            readiness[cap.module] = all(r in registered for r in cap.required)
        else:
            readiness[cap.module] = bool(registered & set(cap.optional))
    return readiness
