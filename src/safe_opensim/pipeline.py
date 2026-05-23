from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .converters import RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS, bvh_timing, convert_bvh_to_rajagopal_trc
from .ik_setup import write_inverse_kinematics_setup
from .opensim_resources import extract_rajagopal_model, find_opensim_cmd


@dataclass(frozen=True)
class RajagopalPipelineResult:
    model_path: Path
    marker_trc_path: Path
    ik_setup_path: Path
    motion_path: Path
    ran_ik: bool


def prepare_rajagopal_ik(
    input_bvh: str | Path,
    output_dir: str | Path,
    *,
    model_file: str | Path | None = None,
    trc_scale: float = 0.01,
    trc_units: str = "m",
    run_ik: bool = False,
    opensim_cmd: str | Path | None = None,
    opensim_log_level: str = "error",
) -> RajagopalPipelineResult:
    """Create Rajagopal-compatible TRC and IK setup files, optionally running IK."""
    source = Path(input_bvh)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    model_path = (
        Path(model_file)
        if model_file is not None
        else extract_rajagopal_model(destination / "models")
    )
    trc_path = destination / f"{source.stem}_rajagopal.trc"
    setup_path = destination / f"{source.stem}_rajagopal_ik_setup.xml"
    motion_path = destination / f"{source.stem}_rajagopal_ik.mot"

    convert_bvh_to_rajagopal_trc(
        source,
        trc_path,
        marker_scale=trc_scale,
        units=trc_units,
    )
    frames, frame_time = bvh_timing(source)
    write_inverse_kinematics_setup(
        setup_path,
        model_file=model_path.resolve(),
        marker_file=trc_path.resolve(),
        output_motion_file=motion_path.resolve(),
        marker_weights=RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS,
        time_range=(0.0, (frames - 1) * frame_time),
    )

    if run_ik:
        command = Path(opensim_cmd) if opensim_cmd is not None else find_opensim_cmd()
        subprocess.run(
            [str(command), f"--log={opensim_log_level}", "run-tool", str(setup_path)],
            check=True,
        )

    return RajagopalPipelineResult(
        model_path=model_path,
        marker_trc_path=trc_path,
        ik_setup_path=setup_path,
        motion_path=motion_path,
        ran_ik=run_ik,
    )
