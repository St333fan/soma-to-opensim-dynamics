from __future__ import annotations

import argparse
import importlib.util
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from .converters import (
    RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS,
    convert_bvh_to_adjusted_ulb_trc,
    convert_bvh_to_improved_ulb_trc,
    convert_bvh_to_storage,
    convert_bvh_to_trc,
    convert_bvh_to_rajagopal_trc,
    convert_g1_csv_to_storage,
    load_column_map,
)
from .ik_setup import write_inverse_kinematics_setup
from .opensim_resources import (
    DEFAULT_OPENSIM_PYTHON,
    find_geometry_dir,
    find_opensim_cmd,
)
from .pipeline import prepare_rajagopal_ik
from .seed_dataset import SeedDataset
from .static_optimization_setup import write_static_optimization_setup


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seed-to-opensim",
        description="Convert BONES-SEED/SOMA motion files into OpenSim-compatible IK inputs.",
    )
    subparsers = parser.add_subparsers(required=True)

    doctor = subparsers.add_parser("doctor", help="inspect conda/OpenSim availability")
    doctor.set_defaults(func=cmd_doctor)

    list_parser = subparsers.add_parser("list", help="search BONES-SEED metadata")
    list_parser.add_argument("--dataset-root", required=True)
    list_parser.add_argument("--query", default="")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.set_defaults(func=cmd_list)

    convert = subparsers.add_parser("convert", help="convert one motion selected from metadata")
    convert.add_argument("--dataset-root", required=True)
    convert.add_argument("--motion", required=True, help="filename or move_name from metadata")
    convert.add_argument(
        "--representation",
        choices=("g1", "soma_uniform", "soma_proportional"),
        default="g1",
    )
    _add_conversion_arguments(convert)
    convert.set_defaults(func=cmd_convert)

    convert_file = subparsers.add_parser("convert-file", help="convert a CSV or BVH file directly")
    convert_file.add_argument("--input", required=True)
    convert_file.add_argument(
        "--kind",
        choices=(
            "g1-csv",
            "bvh",
            "bvh-trc",
            "bvh-rajagopal-trc",
            "bvh-adjusted-ulb-trc",
            "bvh-improved-ulb-trc",
        ),
        required=True,
    )
    _add_conversion_arguments(convert_file)
    convert_file.set_defaults(func=cmd_convert_file)

    ik_setup = subparsers.add_parser("make-ik-setup", help="write an OpenSim IK setup XML")
    ik_setup.add_argument("--model", required=True)
    ik_setup.add_argument("--marker-file", required=True)
    ik_setup.add_argument("--output-motion", required=True)
    ik_setup.add_argument("--setup-output", required=True)
    ik_setup.add_argument("--time-start", type=float, default=0.0)
    ik_setup.add_argument("--time-end", type=float, required=True)
    ik_setup.set_defaults(func=cmd_make_ik_setup)

    static_opt = subparsers.add_parser(
        "static-optimization",
        help="write and optionally run an OpenSim Static Optimization setup XML",
    )
    static_opt.add_argument("--model", required=True)
    static_opt.add_argument("--coordinates-file", required=True, help="IK .mot or coordinates .sto")
    static_opt.add_argument("--setup-output", required=True)
    static_opt.add_argument("--results-dir", required=True)
    static_opt.add_argument("--time-start", type=float, required=True)
    static_opt.add_argument("--time-end", type=float, required=True)
    static_opt.add_argument(
        "--analyze-every",
        type=int,
        default=1,
        help="StaticOptimization step interval: analyze every N step(s)",
    )
    static_opt.add_argument(
        "--filter-coordinates",
        action="store_true",
        help="low-pass filter coordinates_file before Static Optimization",
    )
    static_opt.add_argument(
        "--coordinate-filter-cutoff",
        type=float,
        default=4.0,
        help="low-pass cutoff in Hz when --filter-coordinates is used",
    )
    static_opt.add_argument("--external-loads-file")
    static_opt.add_argument("--activation-exponent", type=float, default=2.0)
    static_opt.add_argument(
        "--ignore-muscle-physiology",
        action="store_true",
        help="disable muscle force-length-velocity relation in Static Optimization",
    )
    static_opt.add_argument(
        "--ignore-model-force-set",
        action="store_true",
        help="do not use the model's force set in Static Optimization",
    )
    static_opt.add_argument("--optimizer-convergence", type=float, default=1e-4)
    static_opt.add_argument("--optimizer-max-iterations", type=int, default=100)
    static_opt.add_argument("--run", action="store_true", help="run opensim-cmd run-tool after writing XML")
    static_opt.add_argument("--opensim-cmd")
    static_opt.add_argument("--opensim-log-level", default="error")
    static_opt.set_defaults(func=cmd_static_optimization)

    rajagopal = subparsers.add_parser(
        "rajagopal-pipeline",
        help="convert a BVH to Rajagopal TRC/IK setup and optionally run IK",
    )
    rajagopal.add_argument("--input", required=True)
    rajagopal.add_argument("--output-dir", required=True)
    rajagopal.add_argument("--model")
    rajagopal.add_argument("--trc-scale", type=float, default=0.01)
    rajagopal.add_argument("--trc-units", default="m")
    rajagopal.add_argument("--run-ik", action="store_true")
    rajagopal.add_argument("--opensim-cmd")
    rajagopal.add_argument("--opensim-log-level", default="error")
    rajagopal.set_defaults(func=cmd_rajagopal_pipeline)

    return parser


def _add_conversion_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", required=True)
    parser.add_argument("--column-map", help="JSON map from source columns/channels to OpenSim labels")
    parser.add_argument("--fps", type=float, default=120.0)
    parser.add_argument("--delimiter", choices=(",", "\\t", ";"), default=None)
    parser.add_argument("--time-column")
    parser.add_argument("--input-angle-unit", choices=("radians", "degrees"), default="radians")
    parser.add_argument("--output-angle-unit", choices=("radians", "degrees"), default="degrees")
    parser.add_argument(
        "--angle-columns",
        default="heuristic",
        help="all, none, heuristic, or regex:<pattern> for CSV angle conversion",
    )
    parser.add_argument(
        "--linear-scale",
        type=float,
        default=1.0,
        help="scale BVH position channels before writing OpenSim storage",
    )
    parser.add_argument(
        "--trc-scale",
        type=float,
        default=0.01,
        help="scale BVH joint positions before writing TRC markers; BONES-SEED BVH appears centimeter-scaled, so default writes meters",
    )
    parser.add_argument("--trc-units", default="m")
    parser.add_argument(
        "--markers",
        help="comma-separated BVH joint names to include in TRC output; default includes all joints",
    )
    parser.add_argument("--storage-name")


def cmd_doctor(_args: argparse.Namespace) -> int:
    print(f"platform.machine: {platform.machine()}")
    print(f"python: {sys.executable}")
    print(f"python.version: {platform.python_version()}")
    print(f"opensim import in current python: {importlib.util.find_spec('opensim')}")
    print()

    conda = shutil.which("conda")
    if conda:
        print(f"conda: {conda}")
        result = subprocess.run(
            [conda, "env", "list"],
            check=False,
            text=True,
            capture_output=True,
        )
        print(result.stdout.rstrip())
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
    else:
        print("conda: not found")
    print()

    try:
        opensim_cmd = find_opensim_cmd()
        print(f"opensim-cmd: {opensim_cmd}")
        _print_file_type(str(opensim_cmd))
        result = subprocess.run(
            [str(opensim_cmd), "--version"],
            check=False,
            text=True,
            capture_output=True,
        )
        print((result.stdout or result.stderr).strip())
    except FileNotFoundError:
        print("opensim-cmd: not found")

    try:
        print(f"opensim geometry: {find_geometry_dir()}")
    except FileNotFoundError as exc:
        print(f"opensim geometry: not found ({exc})")

    if DEFAULT_OPENSIM_PYTHON.exists():
        print(f"opensim python sdk: {DEFAULT_OPENSIM_PYTHON}")
        binding = DEFAULT_OPENSIM_PYTHON / "opensim" / "_simbody.so"
        if binding.exists():
            _print_file_type(str(binding))
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(DEFAULT_OPENSIM_PYTHON)!r}); "
                    "import opensim; "
                    "print(opensim.GetVersion())"
                ),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"opensim python import through SDK: ok ({result.stdout.strip()})")
        else:
            detail = (result.stderr or result.stdout).strip().splitlines()
            print("opensim python import through SDK: failed")
            if detail:
                print(f"  {detail[-1]}")
    return 0


def _print_file_type(path: str) -> None:
    file_tool = shutil.which("file")
    if not file_tool:
        return
    result = subprocess.run(
        [file_tool, path],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.stdout.strip():
        print(result.stdout.strip())


def cmd_list(args: argparse.Namespace) -> int:
    dataset = SeedDataset(args.dataset_root)
    print(f"metadata: {dataset.metadata_path}")
    for record in dataset.search(args.query, limit=args.limit):
        print(record.summary)
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    dataset = SeedDataset(args.dataset_root)
    record = dataset.find_one(args.motion)
    source = dataset.motion_path(record, args.representation)
    kind = "g1-csv" if args.representation == "g1" else "bvh"
    return _convert_source(source, kind, args)


def cmd_convert_file(args: argparse.Namespace) -> int:
    return _convert_source(Path(args.input), args.kind, args)


def _convert_source(source: Path, kind: str, args: argparse.Namespace) -> int:
    delimiter = "\t" if args.delimiter == "\\t" else args.delimiter
    column_map = load_column_map(args.column_map)
    if kind == "g1-csv":
        result = convert_g1_csv_to_storage(
            source,
            args.output,
            fps=args.fps,
            delimiter=delimiter,
            time_column=args.time_column,
            column_map=column_map,
            input_angle_unit=args.input_angle_unit,
            output_angle_unit=args.output_angle_unit,
            angle_columns=args.angle_columns,
            storage_name=args.storage_name,
        )
    elif kind == "bvh":
        result = convert_bvh_to_storage(
            source,
            args.output,
            column_map=column_map,
            linear_scale=args.linear_scale,
            storage_name=args.storage_name,
        )
    elif kind == "bvh-trc":
        marker_names = (
            [marker.strip() for marker in args.markers.split(",") if marker.strip()]
            if args.markers
            else None
        )
        trc_result = convert_bvh_to_trc(
            source,
            args.output,
            marker_scale=args.trc_scale,
            units=args.trc_units,
            marker_names=marker_names,
        )
        print(f"wrote {trc_result.output_path}")
        print(f"frames: {trc_result.frames}")
        print(f"markers: {trc_result.markers}")
        print(f"units: {trc_result.units}")
        return 0
    elif kind == "bvh-rajagopal-trc":
        trc_result = convert_bvh_to_rajagopal_trc(
            source,
            args.output,
            marker_scale=args.trc_scale,
            units=args.trc_units,
        )
        print(f"wrote {trc_result.output_path}")
        print(f"frames: {trc_result.frames}")
        print(f"markers: {trc_result.markers}")
        print(f"units: {trc_result.units}")
        return 0
    elif kind == "bvh-adjusted-ulb-trc":
        trc_result = convert_bvh_to_adjusted_ulb_trc(
            source,
            args.output,
            marker_scale=args.trc_scale,
            units=args.trc_units,
        )
        print(f"wrote {trc_result.output_path}")
        print(f"frames: {trc_result.frames}")
        print(f"markers: {trc_result.markers}")
        print(f"units: {trc_result.units}")
        return 0
    elif kind == "bvh-improved-ulb-trc":
        trc_result = convert_bvh_to_improved_ulb_trc(
            source,
            args.output,
            marker_scale=args.trc_scale,
            units=args.trc_units,
        )
        print(f"wrote {trc_result.output_path}")
        print(f"frames: {trc_result.frames}")
        print(f"markers: {trc_result.markers}")
        print(f"units: {trc_result.units}")
        return 0
    else:
        raise ValueError(f"unsupported conversion kind {kind!r}")

    print(f"wrote {result.output_path}")
    print(f"rows: {result.rows}")
    print(f"columns: {result.columns}")
    print(f"inDegrees: {result.in_degrees}")
    return 0


def cmd_make_ik_setup(args: argparse.Namespace) -> int:
    setup_path = write_inverse_kinematics_setup(
        Path(args.setup_output).resolve(),
        model_file=Path(args.model).resolve(),
        marker_file=Path(args.marker_file).resolve(),
        output_motion_file=Path(args.output_motion).resolve(),
        marker_weights=RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS,
        time_range=(args.time_start, args.time_end),
    )
    print(f"wrote {setup_path}")
    return 0


def cmd_static_optimization(args: argparse.Namespace) -> int:
    setup_path = write_static_optimization_setup(
        Path(args.setup_output).resolve(),
        model_file=Path(args.model).resolve(),
        coordinates_file=Path(args.coordinates_file).resolve(),
        results_directory=Path(args.results_dir).resolve(),
        time_range=(args.time_start, args.time_end),
        analyze_every=args.analyze_every,
        filter_coordinates=args.filter_coordinates,
        coordinate_filter_cutoff=args.coordinate_filter_cutoff,
        external_loads_file=(
            Path(args.external_loads_file).resolve()
            if args.external_loads_file
            else None
        ),
        activation_exponent=args.activation_exponent,
        use_muscle_physiology=not args.ignore_muscle_physiology,
        use_model_force_set=not args.ignore_model_force_set,
        optimizer_convergence_criterion=args.optimizer_convergence,
        optimizer_max_iterations=args.optimizer_max_iterations,
    )
    print(f"wrote {setup_path}")
    print(f"analyze every: {args.analyze_every} step(s)")
    if args.filter_coordinates:
        print(f"coordinate filter: {args.coordinate_filter_cutoff:g} Hz")
    else:
        print("coordinate filter: off")

    if args.run:
        command = Path(args.opensim_cmd).resolve() if args.opensim_cmd else find_opensim_cmd()
        subprocess.run(
            [str(command), f"--log={args.opensim_log_level}", "run-tool", str(setup_path)],
            check=True,
        )
        print("ran Static Optimization")
    return 0


def cmd_rajagopal_pipeline(args: argparse.Namespace) -> int:
    result = prepare_rajagopal_ik(
        args.input,
        args.output_dir,
        model_file=args.model,
        trc_scale=args.trc_scale,
        trc_units=args.trc_units,
        run_ik=args.run_ik,
        opensim_cmd=args.opensim_cmd,
        opensim_log_level=args.opensim_log_level,
    )
    print(f"model: {result.model_path}")
    print(f"markers: {result.marker_trc_path}")
    print(f"ik setup: {result.ik_setup_path}")
    print(f"motion: {result.motion_path}")
    print(f"ran IK: {result.ran_ik}")
    return 0
