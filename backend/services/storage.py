"""Storage layout and artifact path utilities.

Canonical layout:
    data/
      cases/{case_id}/inputs/
      cases/{case_id}/runs/{run_id}/artifacts/
      cases/{case_id}/runs/{run_id}/derived/frontend/
      reference/

Artifact naming:
    {step_run_id}_{artifact_type}.{format}
    e.g. 12_track1_results_json.json
"""

import hashlib
from pathlib import Path

from backend.config.settings import settings

# ---------- Path builders ----------


def cases_root() -> Path:
    return settings.data_root / "cases"


def case_dir(case_id: int) -> Path:
    return cases_root() / str(case_id)


def case_inputs_dir(case_id: int) -> Path:
    return case_dir(case_id) / "inputs"


def run_dir(case_id: int, run_id: int) -> Path:
    return case_dir(case_id) / "runs" / str(run_id)


def run_artifacts_dir(case_id: int, run_id: int) -> Path:
    return run_dir(case_id, run_id) / "artifacts"


def run_derived_dir(case_id: int, run_id: int) -> Path:
    return run_dir(case_id, run_id) / "derived" / "frontend"


def ensure_case_dirs(case_id: int) -> None:
    """Create the full directory tree for a case."""
    case_inputs_dir(case_id).mkdir(parents=True, exist_ok=True)


def ensure_run_dirs(case_id: int, run_id: int) -> None:
    """Create the full directory tree for a run."""
    run_artifacts_dir(case_id, run_id).mkdir(parents=True, exist_ok=True)
    run_derived_dir(case_id, run_id).mkdir(parents=True, exist_ok=True)


# ---------- Artifact naming ----------


def artifact_filename(step_run_id: int, artifact_type: str, fmt: str) -> str:
    """Build canonical artifact filename.

    Examples:
        artifact_filename(12, "track1_results_json", "json") -> "12_track1_results_json.json"
        artifact_filename(5, "cnv_seg", "seg") -> "5_cnv_seg.seg"
    """
    safe_type = artifact_type.replace("/", "_").replace("\\", "_")
    return f"{step_run_id}_{safe_type}.{fmt}"


def artifact_path(case_id: int, run_id: int, step_run_id: int,
                  artifact_type: str, fmt: str) -> Path:
    """Build full path for an artifact file."""
    return run_artifacts_dir(case_id, run_id) / artifact_filename(step_run_id, artifact_type, fmt)


def derived_dataset_path(case_id: int, run_id: int, page: str) -> Path:
    """Build path for a frontend visualization dataset."""
    return run_derived_dir(case_id, run_id) / f"{page}.json"


# ---------- Checksum ----------


def file_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Compute hex digest of a file using the given hash algorithm."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def bytes_checksum(data: bytes, algorithm: str = "sha256") -> str:
    """Compute hex digest of in-memory bytes."""
    return hashlib.new(algorithm, data).hexdigest()


def dir_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Compute a deterministic hash over all files in a directory tree.

    Files are sorted by relative path so the result is reproducible.
    """
    h = hashlib.new(algorithm)
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            h.update(str(file_path.relative_to(path)).encode())
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
    return h.hexdigest()


def dir_total_size(path: Path) -> int:
    """Sum of all file sizes in a directory tree."""
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def path_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Compute checksum for a file or directory."""
    if path.is_dir():
        return dir_checksum(path, algorithm)
    return file_checksum(path, algorithm)


def path_size(path: Path) -> int:
    """Get size of a file or total size of a directory tree."""
    if path.is_dir():
        return dir_total_size(path)
    return path.stat().st_size


def unique_input_name(base_name: str, step_run_id: int) -> str:
    """Generate a collision-safe name by prepending the step_run_id."""
    return f"{step_run_id}_{base_name}"
