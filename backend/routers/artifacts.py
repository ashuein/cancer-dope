"""Artifact download and listing endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.db.database import get_db
from backend.db.repositories import ArtifactRepository
from backend.models.schemas import ArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _is_path_within(file_path: Path, root: Path) -> bool:
    """Check that file_path is contained within root, blocking traversal."""
    try:
        file_path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: int, db: AsyncSession = Depends(get_db)):
    repo = ArtifactRepository(db)
    artifact = await repo.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: int, db: AsyncSession = Depends(get_db)):
    repo = ArtifactRepository(db)
    artifact = await repo.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    file_path = Path(artifact.path)

    if not _is_path_within(file_path, settings.data_root):
        raise HTTPException(status_code=403, detail="Artifact path outside data root")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream",
    )
