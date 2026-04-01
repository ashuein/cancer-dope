"""AnnData (.h5ad) and Zarr directory validators.

AnnData files are HDF5 with specific group structure (obs, var, X, etc.).
Zarr stores are directories with .zgroup or .zarray markers.
"""

from pathlib import Path

from backend.models.inputs import InputType, InputValidationResult, ValidationIssue

_HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"


def validate_anndata(path: Path) -> InputValidationResult:
    """Validate an AnnData (.h5ad) file by checking HDF5 magic bytes and key groups."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.ANNDATA, filename=path.name, valid=False, issues=issues,
        )

    # Check HDF5 magic bytes
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
    except Exception as e:
        issues.append(ValidationIssue(field="file", message=f"Cannot read file: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.ANNDATA, filename=path.name, valid=False, issues=issues,
        )

    if magic != _HDF5_MAGIC:
        issues.append(ValidationIssue(
            field="format", message="Not a valid HDF5 file (wrong magic bytes)", severity="error",
        ))
        return InputValidationResult(
            input_type=InputType.ANNDATA, filename=path.name, valid=False, issues=issues,
        )

    summary["format"] = "h5ad"
    summary["size_bytes"] = path.stat().st_size

    # Inspect HDF5 groups — this is required validation, not optional
    try:
        import h5py

        with h5py.File(path, "r") as h5:
            top_keys = list(h5.keys())
            summary["top_level_keys"] = top_keys

            expected_keys = {"obs", "var", "X"}
            found = expected_keys & set(top_keys)
            missing = expected_keys - found
            if missing:
                issues.append(ValidationIssue(
                    field="structure",
                    message=f"Missing expected AnnData groups: {', '.join(sorted(missing))}",
                    severity="error",
                ))
            if "obs" in h5:
                try:
                    obs = h5["obs"]
                    summary["n_obs"] = obs.attrs.get("_index", obs).shape[0] if hasattr(obs, "shape") else "unknown"
                except Exception:
                    summary["n_obs"] = "unknown"
    except ImportError:
        issues.append(ValidationIssue(
            field="dependency",
            message="h5py not installed — cannot validate AnnData structure",
            severity="warning",
        ))
    except Exception as e:
        issues.append(ValidationIssue(
            field="structure", message=f"Corrupt or unreadable HDF5 file: {e}", severity="error",
        ))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.ANNDATA, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )


def validate_zarr(path: Path) -> InputValidationResult:
    """Validate a Zarr store by checking directory structure markers."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.exists():
        issues.append(ValidationIssue(field="path", message="Path not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.ZARR, filename=path.name, valid=False, issues=issues,
        )

    if not path.is_dir():
        issues.append(ValidationIssue(
            field="format", message="Zarr store must be a directory", severity="error",
        ))
        return InputValidationResult(
            input_type=InputType.ZARR, filename=path.name, valid=False, issues=issues,
        )

    # Check for Zarr markers
    has_zgroup = (path / ".zgroup").is_file()
    has_zarray = (path / ".zarray").is_file()
    has_zattrs = (path / ".zattrs").is_file()

    if not (has_zgroup or has_zarray):
        issues.append(ValidationIssue(
            field="format",
            message="Not a valid Zarr store — missing .zgroup and .zarray markers",
            severity="error",
        ))
    else:
        summary["is_group"] = has_zgroup
        summary["is_array"] = has_zarray
        summary["has_attrs"] = has_zattrs

        # List top-level sub-arrays/groups
        children = [d.name for d in path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        summary["children"] = children[:20]  # cap for large stores

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.ZARR, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )
