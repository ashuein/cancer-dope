"""Health check and version endpoints."""

from fastapi import APIRouter

from backend.config.settings import settings
from backend.models.schemas import HealthResponse, ModuleStatus

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        environment=settings.app_env,
    )


@router.get("/version")
async def version():
    return {"version": APP_VERSION, "app": settings.app_name}


@router.get("/modules", response_model=list[ModuleStatus])
async def list_modules():
    modules = [
        ("timeline", settings.module_timeline),
        ("track1", settings.module_track1),
        ("track2", settings.module_track2),
        ("bulk_rna", settings.module_bulk_rna),
        ("scrna", settings.module_scrna),
        ("gsea", settings.module_gsea),
        ("cnv", settings.module_cnv),
        ("bam", settings.module_bam),
        ("imaging", settings.module_imaging),
        ("spatial", settings.module_spatial),
    ]
    return [ModuleStatus(name=name, enabled=enabled) for name, enabled in modules]
