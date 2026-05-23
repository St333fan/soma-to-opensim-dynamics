from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from safe_opensim.converters import (
    IMPROVED_ULB_MARKER_WEIGHTS,
    bvh_timing,
    convert_bvh_to_improved_ulb_trc,
)
from safe_opensim.ik_setup import write_inverse_kinematics_setup
from safe_opensim.opensim_resources import find_opensim_cmd


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a SOMA-X BVH to an improved ULB TRC and run OpenSim IK."
    )
    parser.add_argument(
        "--input",
        default="examples/data/nailing_wall_R_003__A282.bvh",
        help="Input SOMA-X/BONES-SEED BVH file.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Path to the OpenSim model, for example Adjusted_ULBmodel.osim.",
    )
    parser.add_argument(
        "--output-dir",
        default="output/example_improved_ulb",
        help="Directory for TRC, IK setup, MOT, and marker error files.",
    )
    parser.add_argument(
        "--opensim-cmd",
        default=None,
        help="Optional path to opensim-cmd. If omitted, PATH and common OpenSim 4.5 installs are checked.",
    )
    parser.add_argument("--log-level", default="error")
    args = parser.parse_args()

    bvh = Path(args.input).resolve()
    model = Path(args.model).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = bvh.stem
    trc = output_dir / f"{stem}_Improved_ULBmodel.trc"
    mot = output_dir / f"{stem}_Improved_ULBmodel_IK.mot"
    setup = output_dir / f"{stem}_Improved_ULBmodel_IK_settings.xml"

    trc_result = convert_bvh_to_improved_ulb_trc(bvh, trc)
    frames, frame_time = bvh_timing(bvh)
    time_end = (frames - 1) * frame_time

    write_inverse_kinematics_setup(
        setup,
        model_file=model,
        marker_file=trc,
        output_motion_file=mot,
        marker_weights=IMPROVED_ULB_MARKER_WEIGHTS,
        time_range=(0.0, time_end),
    )

    command = Path(args.opensim_cmd).resolve() if args.opensim_cmd else find_opensim_cmd()
    subprocess.run(
        [str(command), f"--log={args.log_level}", "run-tool", str(setup)],
        check=True,
    )

    print(f"BVH frames: {frames}")
    print(f"Time range: 0.000000 to {time_end:.6f}")
    print(f"Markers: {trc_result.markers}")
    print(f"TRC: {trc}")
    print(f"IK setup: {setup}")
    print(f"MOT: {mot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
