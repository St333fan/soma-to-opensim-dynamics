from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path


DEFAULT_OPENSIM_INSTALL = Path(os.environ.get("OPENSIM_HOME", "C:/OpenSim 4.5"))
DEFAULT_OPENSIM_RESOURCE_ROOT = DEFAULT_OPENSIM_INSTALL
DEFAULT_OPENSIM_CMD = DEFAULT_OPENSIM_INSTALL / "bin" / "opensim-cmd.exe"
DEFAULT_OPENSIM_PYTHON = DEFAULT_OPENSIM_RESOURCE_ROOT / "sdk" / "Python"
DEFAULT_RESOURCES_ZIP = DEFAULT_OPENSIM_RESOURCE_ROOT / "Resources.zip"
DEFAULT_GEOMETRY_DIR = DEFAULT_OPENSIM_RESOURCE_ROOT / "Geometry"
RAJAGOPAL_MODEL_ARCHIVE_PATH = "Models/Rajagopal/Rajagopal2016.osim"


def find_opensim_cmd() -> Path:
    discovered = shutil.which("opensim-cmd")
    if discovered:
        return Path(discovered)
    if DEFAULT_OPENSIM_CMD.exists():
        return DEFAULT_OPENSIM_CMD
    raise FileNotFoundError(
        "opensim-cmd was not found on PATH or at the default OpenSim 4.5 install path"
    )


def find_resources_zip() -> Path:
    if DEFAULT_RESOURCES_ZIP.exists():
        return DEFAULT_RESOURCES_ZIP
    raise FileNotFoundError(f"OpenSim Resources.zip was not found at {DEFAULT_RESOURCES_ZIP}")


def find_geometry_dir() -> Path:
    if DEFAULT_GEOMETRY_DIR.exists():
        return DEFAULT_GEOMETRY_DIR
    raise FileNotFoundError(f"OpenSim Geometry directory was not found at {DEFAULT_GEOMETRY_DIR}")


def extract_rajagopal_model(
    destination_dir: str | Path,
    *,
    resources_zip: str | Path | None = None,
) -> Path:
    """Extract the bundled Rajagopal2016 model and return its local path."""
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)
    model_path = destination / "Rajagopal2016.osim"
    archive = Path(resources_zip) if resources_zip is not None else find_resources_zip()

    with zipfile.ZipFile(archive) as handle:
        with handle.open(RAJAGOPAL_MODEL_ARCHIVE_PATH) as source, model_path.open("wb") as target:
            target.write(source.read())
    return model_path
