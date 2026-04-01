"""Application settings loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "PrecisionOncology"
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/metadata.db"

    # Paths
    data_root: Path = Path("./data")
    upload_dir: Path = Path("./data/uploads")
    cache_dir: Path = Path("./data/cache")
    reference_dir: Path = Path("./data/reference")

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    cors_origins: list[str] = ["http://localhost:5173"]

    # External APIs
    alphafold_server_url: str = "https://alphafoldserver.com"
    af3_daily_limit: int = 20
    hf_api_token: str = ""
    reactome_base_url: str = "https://reactome.org/ContentService"
    chembl_base_url: str = "https://www.ebi.ac.uk/chembl/api/data"
    dgidb_base_url: str = "https://dgidb.org/api/graphql"
    gtex_base_url: str = "https://gtexportal.org/api/v2"
    pkcsm_base_url: str = "http://biosig.lab.uq.edu.au/pkcsm"
    ensembl_vep_url: str = "https://rest.ensembl.org"

    # Tool paths
    netmhcpan_path: str = ""

    # Module flags
    module_timeline: bool = True
    module_track1: bool = True
    module_track2: bool = True
    module_bulk_rna: bool = True
    module_scrna: bool = True
    module_gsea: bool = True
    module_cnv: bool = True
    module_bam: bool = True
    module_imaging: bool = True
    module_spatial: bool = True

    # Rate limits
    api_rate_limit: int = 100
    api_rate_window: int = 60

    # Artifacts
    max_upload_size_mb: int = 500
    artifact_retention_days: int = 90

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()
