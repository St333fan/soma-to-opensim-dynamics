from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .opensim_storage import sanitize_label, write_storage


TIME_COLUMN_CANDIDATES = {"time", "t", "timestamp", "seconds", "sec"}
FRAME_COLUMN_CANDIDATES = {"frame", "frames", "frame_index", "index"}
LINEAR_HINTS = (
    "position",
    "translation",
    "trans",
    "linear",
    "height",
    "root_x",
    "root_y",
    "root_z",
)
QUATERNION_HINTS = ("quat", "quaternion", "qw", "qx", "qy", "qz")


@dataclass(frozen=True)
class ConversionResult:
    input_path: Path
    output_path: Path
    rows: int
    columns: int
    labels: tuple[str, ...]
    in_degrees: bool | None


@dataclass(frozen=True)
class TrcConversionResult:
    input_path: Path
    output_path: Path
    frames: int
    markers: int
    marker_names: tuple[str, ...]
    units: str


RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS: dict[str, float] = {
    "RACR": 10,
    "LACR": 10,
    "C7": 5,
    "CLAV": 5,
    "RASI": 25,
    "LASI": 25,
    "RPSI": 15,
    "LPSI": 15,
    "RLEL": 8,
    "LLEL": 8,
    "RFAradius": 5,
    "LFAradius": 5,
    "RKJC": 15,
    "LKJC": 15,
    "RAJC": 15,
    "LAJC": 15,
    "RCAL": 8,
    "LCAL": 8,
    "RTOE": 8,
    "LTOE": 8,
    "RMT5": 4,
    "LMT5": 4,
}


ADJUSTED_ULB_MARKER_WEIGHTS: dict[str, float] = {
    "STRN": 1.0,
    "RSHO": 1.0,
    "LSHO": 1.0,
    "C7": 1.0,
    "T10": 1.0,
    "CLAV": 1.0,
    "RUPA": 0.5,
    "RELB": 1.0,
    "RFRM": 0.5,
    "RWRA": 1.0,
    "RWRB": 1.0,
    "LUPA": 0.5,
    "LELB": 1.0,
    "LFRM": 0.5,
    "LWRA": 1.0,
    "LWRB": 1.0,
    "RASI": 1.0,
    "LASI": 1.0,
    "RTHI": 0.5,
    "RKNE": 1.0,
    "LTHI": 0.5,
    "LKNE": 1.0,
    "LPSI": 1.0,
    "RPSI": 1.0,
    "RANK": 1.0,
    "LANK": 1.0,
    "RTOE": 0.5,
    "LTOE": 0.5,
    "RHEE": 1.0,
    "LHEE": 1.0,
    "LFHD": 0.5,
    "RFHD": 0.5,
    "LBHD": 0.5,
    "RBHD": 0.5,
    "RBAK": 1.0,
    "LFIN": 0.5,
    "RFIN": 0.5,
    "RTIB": 1.0,
    "LTIB": 1.0,
}


IMPROVED_ULB_MARKER_ANCHORS: dict[str, tuple[str, tuple[float, float, float]]] = {
    "STRN": ("LeftShoulder", (-0.01302022, -0.12474632, 0.07130794)),
    "RSHO": ("RightArm", (0.00514348, 0.07539399, 0.03723440)),
    "LSHO": ("LeftArm", (-0.00011192, 0.07035750, 0.03327106)),
    "C7": ("Neck1", (-0.00035797, 0.03408499, -0.05584473)),
    "T10": ("Chest", (0.00498882, 0.07171955, -0.07590323)),
    "CLAV": ("RightShoulder", (0.01156008, 0.03595265, 0.00869391)),
    "RUPA": ("RightArm", (-0.12727669, -0.00717391, -0.02705229)),
    "RELB": ("RightForeArm", (-0.00219947, -0.01346873, -0.02294206)),
    "RFRM": ("RightHand", (0.12801593, -0.01395364, -0.02173237)),
    "RWRA": ("RightHandThumb1", (0.02177093, 0.00519178, 0.00492597)),
    "RWRB": ("RightHand", (0.00577436, -0.00176328, -0.03288034)),
    "LUPA": ("LeftArm", (0.12967268, -0.02863218, -0.01710814)),
    "LELB": ("LeftForeArm", (0.00792964, -0.02616837, -0.02322741)),
    "LFRM": ("LeftHand", (-0.11102367, -0.01273159, -0.01596505)),
    "LWRA": ("LeftHandThumb1", (-0.01812232, -0.00806060, -0.00725394)),
    "LWRB": ("LeftHand", (-0.00356021, -0.01013870, -0.02215985)),
    "RASI": ("RightLeg", (-0.04248854, 0.07258396, 0.10415630)),
    "LASI": ("LeftLeg", (0.03982891, 0.07411705, 0.10294658)),
    "RTHI": ("RightShin", (-0.05027262, 0.20018599, 0.03722061)),
    "RKNE": ("RightShin", (-0.03974000, -0.00281151, 0.02619395)),
    "LTHI": ("LeftLeg", (0.05804123, -0.20469472, 0.05361690)),
    "LKNE": ("LeftShin", (0.03269206, -0.01152405, 0.02407070)),
    "LPSI": ("Hips", (0.06536497, 0.01579065, -0.03711338)),
    "RPSI": ("Hips", (-0.06150558, 0.01237378, -0.03883985)),
    "RANK": ("RightFoot", (-0.04165136, -0.00453217, 0.02359593)),
    "LANK": ("LeftFoot", (0.04301911, -0.00534662, 0.01686387)),
    "RTOE": ("RightToeEnd", (0.00936681, -0.00371590, -0.01104295)),
    "LTOE": ("LeftToeEnd", (-0.00508954, -0.00262448, -0.01097926)),
    "RHEE": ("RightFoot", (0.01124349, -0.03887045, -0.04706701)),
    "LHEE": ("LeftFoot", (-0.00469775, -0.04661900, -0.04733971)),
    "LFHD": ("LeftEye", (0.01964617, 0.05647565, -0.01714687)),
    "RFHD": ("RightEye", (-0.01534189, 0.06075496, -0.00913542)),
    "LBHD": ("HeadEnd", (0.05662651, -0.04296591, -0.07236566)),
    "RBHD": ("HeadEnd", (-0.05610814, -0.04398169, -0.06745717)),
    "RBAK": ("RightArm", (0.06473708, -0.07694648, -0.09735491)),
    "LFIN": ("LeftHandMiddle2", (0.00599710, -0.01187466, 0.00503048)),
    "RFIN": ("RightHandMiddle2", (-0.00747826, 0.00490468, 0.00341037)),
    "RTIB": ("RightFoot", (-0.02719043, 0.18781957, 0.03142202)),
    "LTIB": ("LeftFoot", (0.02850165, 0.17326652, 0.03143493)),
}


IMPROVED_ULB_MARKER_WEIGHTS: dict[str, float] = {
    marker_name: ADJUSTED_ULB_MARKER_WEIGHTS.get(marker_name, 1.0)
    for marker_name in IMPROVED_ULB_MARKER_ANCHORS
}


TRC_MARKER_SETS: dict[str, dict[str, float]] = {
    "rajagopal": RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS,
    "adjusted_ulb": ADJUSTED_ULB_MARKER_WEIGHTS,
    "improved_ulb": IMPROVED_ULB_MARKER_WEIGHTS,
}


def load_column_map(path: str | Path | None) -> dict[str, str | None]:
    if path is None:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("column map must be a JSON object")
    mapping: dict[str, str | None] = {}
    for key, value in data.items():
        if value is None or value is False or value == "":
            mapping[str(key)] = None
        else:
            mapping[str(key)] = str(value)
    return mapping


def convert_g1_csv_to_storage(
    input_csv: str | Path,
    output_path: str | Path,
    *,
    fps: float = 120.0,
    delimiter: str | None = None,
    time_column: str | None = None,
    column_map: dict[str, str | None] | None = None,
    input_angle_unit: str = "radians",
    output_angle_unit: str = "degrees",
    angle_columns: str = "heuristic",
    storage_name: str | None = None,
) -> ConversionResult:
    """Convert a BONES-SEED G1 MuJoCo CSV trajectory to OpenSim storage."""
    source = Path(input_csv)
    mapping = column_map or {}
    header, records = _read_csv_records(source, delimiter=delimiter)
    if not records:
        raise ValueError(f"{source} has no data rows")

    time_key = _choose_time_column(header, time_column)
    selected_columns: list[tuple[str, str]] = []
    for key in header:
        if key == time_key or key.strip().lower() in FRAME_COLUMN_CANDIDATES:
            continue
        if key in mapping and mapping[key] is None:
            continue
        label = mapping.get(key, sanitize_label(key))
        selected_columns.append((key, label))

    if not selected_columns:
        raise ValueError("no data columns selected for output")

    labels = ("time",) + tuple(label for _, label in selected_columns)
    multiplier = _angle_multiplier(input_angle_unit, output_angle_unit)
    angle_column_names = {
        key
        for key, _ in selected_columns
        if _is_angle_column(key, mode=angle_columns)
    }

    rows: list[list[float]] = []
    for row_index, record in enumerate(records):
        time_value = (
            _parse_float(record[time_key], time_key, row_index + 2)
            if time_key is not None
            else row_index / fps
        )
        output_row = [time_value]
        for key, _label in selected_columns:
            value = _parse_float(record[key], key, row_index + 2)
            if key in angle_column_names:
                value *= multiplier
            output_row.append(value)
        rows.append(output_row)

    in_degrees = output_angle_unit == "degrees"
    name = storage_name or source.stem
    row_count = write_storage(
        output_path,
        name=name,
        labels=labels,
        rows=rows,
        in_degrees=in_degrees,
    )
    return ConversionResult(
        input_path=source,
        output_path=Path(output_path),
        rows=row_count,
        columns=len(labels),
        labels=labels,
        in_degrees=in_degrees,
    )


def convert_bvh_to_storage(
    input_bvh: str | Path,
    output_path: str | Path,
    *,
    column_map: dict[str, str | None] | None = None,
    linear_scale: float = 1.0,
    storage_name: str | None = None,
) -> ConversionResult:
    """Export BVH channel values as an OpenSim storage table."""
    source = Path(input_bvh)
    bvh = _parse_bvh(source)
    mapping = column_map or {}

    selected: list[tuple[int, str, bool]] = []
    for index, label in enumerate(bvh.channel_labels):
        if label in mapping and mapping[label] is None:
            continue
        output_label = mapping.get(label, sanitize_label(label))
        is_position = label.lower().endswith("position")
        selected.append((index, output_label, is_position))

    if not selected:
        raise ValueError("no BVH channels selected for output")

    labels = ("time",) + tuple(label for _, label, _ in selected)
    rows: list[list[float]] = []
    for frame_index, frame in enumerate(bvh.frames):
        output_row = [frame_index * bvh.frame_time]
        for channel_index, _label, is_position in selected:
            value = frame[channel_index]
            if is_position:
                value *= linear_scale
            output_row.append(value)
        rows.append(output_row)

    name = storage_name or source.stem
    row_count = write_storage(
        output_path,
        name=name,
        labels=labels,
        rows=rows,
        in_degrees=True,
    )
    return ConversionResult(
        input_path=source,
        output_path=Path(output_path),
        rows=row_count,
        columns=len(labels),
        labels=labels,
        in_degrees=True,
    )


def convert_bvh_to_trc(
    input_bvh: str | Path,
    output_path: str | Path,
    *,
    marker_scale: float = 0.01,
    units: str = "m",
    marker_names: list[str] | None = None,
) -> TrcConversionResult:
    """Convert BVH joint world positions to an OpenSim TRC marker trajectory."""
    source = Path(input_bvh)
    bvh = _parse_bvh(source)
    requested = set(marker_names or [])
    markers = tuple(
        joint.name
        for joint in bvh.joints
        if not requested or joint.name in requested
    )
    if not markers:
        raise ValueError("no BVH joints selected for TRC output")

    positions_by_frame = [
        _bvh_global_positions(bvh, frame, scale=marker_scale)
        for frame in bvh.frames
    ]
    _write_trc(
        output_path,
        source_name=source.name,
        data_rate=1.0 / bvh.frame_time,
        frame_time=bvh.frame_time,
        marker_names=markers,
        positions_by_frame=positions_by_frame,
        units=units,
    )
    return TrcConversionResult(
        input_path=source,
        output_path=Path(output_path),
        frames=len(bvh.frames),
        markers=len(markers),
        marker_names=markers,
        units=units,
    )


def convert_bvh_to_rajagopal_trc(
    input_bvh: str | Path,
    output_path: str | Path,
    *,
    marker_scale: float = 0.01,
    units: str = "m",
) -> TrcConversionResult:
    """Convert BVH joints into virtual markers matching the Rajagopal marker set."""
    source = Path(input_bvh)
    bvh = _parse_bvh(source)
    marker_names = tuple(RAJAGOPAL_VIRTUAL_MARKER_WEIGHTS)
    positions_by_frame = [
        _rajagopal_virtual_markers(
            _bvh_global_positions(bvh, frame, scale=marker_scale)
        )
        for frame in bvh.frames
    ]
    _write_trc(
        output_path,
        source_name=source.name,
        data_rate=1.0 / bvh.frame_time,
        frame_time=bvh.frame_time,
        marker_names=marker_names,
        positions_by_frame=positions_by_frame,
        units=units,
    )
    return TrcConversionResult(
        input_path=source,
        output_path=Path(output_path),
        frames=len(bvh.frames),
        markers=len(marker_names),
        marker_names=marker_names,
        units=units,
    )


def convert_bvh_to_adjusted_ulb_trc(
    input_bvh: str | Path,
    output_path: str | Path,
    *,
    marker_scale: float = 0.01,
    units: str = "m",
) -> TrcConversionResult:
    """Convert BVH joints into virtual markers matching Adjusted_ULBmodel.osim."""
    source = Path(input_bvh)
    bvh = _parse_bvh(source)
    marker_names = tuple(ADJUSTED_ULB_MARKER_WEIGHTS)
    positions_by_frame = [
        _adjusted_ulb_virtual_markers(
            _bvh_global_positions(bvh, frame, scale=marker_scale)
        )
        for frame in bvh.frames
    ]
    _write_trc(
        output_path,
        source_name=source.name,
        data_rate=1.0 / bvh.frame_time,
        frame_time=bvh.frame_time,
        marker_names=marker_names,
        positions_by_frame=positions_by_frame,
        units=units,
    )
    return TrcConversionResult(
        input_path=source,
        output_path=Path(output_path),
        frames=len(bvh.frames),
        markers=len(marker_names),
        marker_names=marker_names,
        units=units,
    )


def convert_bvh_to_improved_ulb_trc(
    input_bvh: str | Path,
    output_path: str | Path,
    *,
    marker_scale: float = 0.01,
    units: str = "m",
) -> TrcConversionResult:
    """Convert BVH joints into hardcoded improved ULB virtual markers."""
    source = Path(input_bvh)
    bvh = _parse_bvh(source)
    marker_names = tuple(IMPROVED_ULB_MARKER_WEIGHTS)
    positions_by_frame = [
        _improved_ulb_virtual_markers(
            _bvh_global_positions(bvh, frame, scale=marker_scale)
        )
        for frame in bvh.frames
    ]
    _write_trc(
        output_path,
        source_name=source.name,
        data_rate=1.0 / bvh.frame_time,
        frame_time=bvh.frame_time,
        marker_names=marker_names,
        positions_by_frame=positions_by_frame,
        units=units,
    )
    return TrcConversionResult(
        input_path=source,
        output_path=Path(output_path),
        frames=len(bvh.frames),
        markers=len(marker_names),
        marker_names=marker_names,
        units=units,
    )


def bvh_timing(input_bvh: str | Path) -> tuple[int, float]:
    bvh = _parse_bvh(Path(input_bvh))
    return len(bvh.frames), bvh.frame_time


def _read_csv_records(path: Path, *, delimiter: str | None) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        dialect: Any | None = None
        if delimiter is None:
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
            except csv.Error:
                dialect = csv.excel
        reader = (
            csv.DictReader(handle, dialect=dialect)
            if delimiter is None
            else csv.DictReader(handle, delimiter=delimiter)
        )
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        header = [field.strip() for field in reader.fieldnames]
        records: list[dict[str, str]] = []
        for row in reader:
            records.append({key.strip(): value for key, value in row.items() if key is not None})
    return header, records


def _choose_time_column(header: list[str], requested: str | None) -> str | None:
    if requested:
        if requested not in header:
            raise ValueError(f"time column {requested!r} not found in CSV header")
        return requested
    for key in header:
        if key.strip().lower() in TIME_COLUMN_CANDIDATES:
            return key
    return None


def _parse_float(value: str, column: str, line_number: int) -> float:
    if value is None or value == "":
        raise ValueError(f"blank numeric value in column {column!r} on line {line_number}")
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"non-numeric value {value!r} in column {column!r} on line {line_number}"
        ) from exc


def _angle_multiplier(input_unit: str, output_unit: str) -> float:
    normalized_input = input_unit.lower()
    normalized_output = output_unit.lower()
    valid = {"radians", "degrees"}
    if normalized_input not in valid:
        raise ValueError(f"input angle unit must be one of {sorted(valid)}")
    if normalized_output not in valid:
        raise ValueError(f"output angle unit must be one of {sorted(valid)}")
    if normalized_input == normalized_output:
        return 1.0
    if normalized_input == "radians" and normalized_output == "degrees":
        return 180.0 / math.pi
    return math.pi / 180.0


def _is_angle_column(column_name: str, *, mode: str) -> bool:
    mode = mode.strip()
    if mode == "all":
        return True
    if mode == "none":
        return False
    if mode.startswith("regex:"):
        return re.search(mode.removeprefix("regex:"), column_name) is not None
    if mode != "heuristic":
        raise ValueError("angle-columns must be all, none, heuristic, or regex:<pattern>")

    name = column_name.strip().lower()
    if name in TIME_COLUMN_CANDIDATES or name in FRAME_COLUMN_CANDIDATES:
        return False
    if any(hint in name for hint in QUATERNION_HINTS):
        return False
    if any(hint in name for hint in LINEAR_HINTS):
        return False
    if re.search(r"(^|_)(tx|ty|tz|x|y|z)$", name):
        return False
    return True


@dataclass(frozen=True)
class _BvhData:
    channel_labels: tuple[str, ...]
    frame_time: float
    frames: tuple[tuple[float, ...], ...]
    joints: tuple["_BvhJoint", ...]


@dataclass(frozen=True)
class _BvhJoint:
    name: str
    parent: int | None
    offset: tuple[float, float, float]
    channels: tuple[str, ...]
    channel_start: int


def _parse_bvh(path: Path) -> _BvhData:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = [line.rstrip() for line in handle]

    channel_labels: list[str] = []
    joints: list[dict[str, Any]] = []
    joint_stack: list[int] = []
    pending_joint: str | None = None
    motion_index: int | None = None

    for line_index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line == "MOTION":
            motion_index = line_index
            break
        parts = line.split()
        if not parts:
            continue
        if parts[0] in {"ROOT", "JOINT"} and len(parts) >= 2:
            pending_joint = sanitize_label(parts[1])
        elif parts[0] == "End":
            parent_name = joints[joint_stack[-1]]["name"] if joint_stack else "End"
            pending_joint = sanitize_label(f"{parent_name}EndSite")
        elif parts[0] == "{":
            if pending_joint is not None:
                parent = joint_stack[-1] if joint_stack else None
                joints.append(
                    {
                        "name": pending_joint,
                        "parent": parent,
                        "offset": (0.0, 0.0, 0.0),
                        "channels": (),
                        "channel_start": len(channel_labels),
                    }
                )
                joint_stack.append(len(joints) - 1)
                pending_joint = None
        elif parts[0] == "}":
            if joint_stack:
                joint_stack.pop()
        elif parts[0] == "OFFSET":
            if not joint_stack:
                raise ValueError(f"OFFSET declared outside a joint at line {line_index + 1}")
            joints[joint_stack[-1]]["offset"] = tuple(float(value) for value in parts[1:4])
        elif parts[0] == "CHANNELS":
            if not joint_stack:
                raise ValueError(f"CHANNELS declared outside a joint at line {line_index + 1}")
            count = int(parts[1])
            channels = parts[2 : 2 + count]
            if len(channels) != count:
                raise ValueError(f"CHANNELS count mismatch at line {line_index + 1}")
            joint = joints[joint_stack[-1]]
            joint["channels"] = tuple(channels)
            joint["channel_start"] = len(channel_labels)
            joint_name = joint["name"]
            for channel in channels:
                channel_labels.append(f"{joint_name}_{channel}")

    if motion_index is None:
        raise ValueError(f"{path} does not contain a MOTION section")
    if not channel_labels:
        raise ValueError(f"{path} does not declare any BVH channels")

    frame_count: int | None = None
    frame_time: float | None = None
    data_start: int | None = None
    for line_index in range(motion_index + 1, len(lines)):
        line = lines[line_index].strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("frames:"):
            frame_count = int(line.split(":", 1)[1].strip())
        elif lower.startswith("frame time:"):
            frame_time = float(line.split(":", 1)[1].strip())
            data_start = line_index + 1
            break

    if frame_count is None:
        raise ValueError(f"{path} MOTION section is missing Frames")
    if frame_time is None or data_start is None:
        raise ValueError(f"{path} MOTION section is missing Frame Time")

    frames: list[tuple[float, ...]] = []
    expected_width = len(channel_labels)
    for raw_line in lines[data_start:]:
        line = raw_line.strip()
        if not line:
            continue
        values = tuple(float(value) for value in line.split())
        if len(values) != expected_width:
            raise ValueError(
                f"BVH frame has {len(values)} values, expected {expected_width}"
            )
        frames.append(values)

    if len(frames) != frame_count:
        raise ValueError(f"BVH declares {frame_count} frames but contains {len(frames)}")

    return _BvhData(
        channel_labels=tuple(channel_labels),
        frame_time=frame_time,
        frames=tuple(frames),
        joints=tuple(
            _BvhJoint(
                name=joint["name"],
                parent=joint["parent"],
                offset=joint["offset"],
                channels=joint["channels"],
                channel_start=joint["channel_start"],
            )
            for joint in joints
        ),
    )


def _bvh_global_positions(
    bvh: _BvhData,
    frame: tuple[float, ...],
    *,
    scale: float,
) -> dict[str, tuple[float, float, float]]:
    global_positions: list[tuple[float, float, float]] = []
    global_rotations: list[tuple[tuple[float, float, float], ...]] = []

    for joint in bvh.joints:
        local_translation = _joint_translation(joint, frame)
        local_rotation = _joint_rotation(joint, frame)
        if joint.parent is None:
            position = local_translation
            rotation = local_rotation
        else:
            parent_position = global_positions[joint.parent]
            parent_rotation = global_rotations[joint.parent]
            rotated_translation = _mat_vec(parent_rotation, local_translation)
            position = _vec_add(parent_position, rotated_translation)
            rotation = _mat_mul(parent_rotation, local_rotation)
        global_positions.append(position)
        global_rotations.append(rotation)

    return {
        joint.name: (
            global_positions[index][0] * scale,
            global_positions[index][1] * scale,
            global_positions[index][2] * scale,
        )
        for index, joint in enumerate(bvh.joints)
    }


def _joint_translation(joint: _BvhJoint, frame: tuple[float, ...]) -> tuple[float, float, float]:
    has_position_channels = any(channel.endswith("position") for channel in joint.channels)
    values = [0.0, 0.0, 0.0] if has_position_channels else list(joint.offset)
    for offset, channel in enumerate(joint.channels):
        if channel == "Xposition":
            values[0] = frame[joint.channel_start + offset]
        elif channel == "Yposition":
            values[1] = frame[joint.channel_start + offset]
        elif channel == "Zposition":
            values[2] = frame[joint.channel_start + offset]
    return (values[0], values[1], values[2])


def _joint_rotation(
    joint: _BvhJoint,
    frame: tuple[float, ...],
) -> tuple[tuple[float, float, float], ...]:
    rotation = _identity_matrix()
    for offset, channel in enumerate(joint.channels):
        if not channel.endswith("rotation"):
            continue
        angle = math.radians(frame[joint.channel_start + offset])
        if channel == "Xrotation":
            axis_rotation = _rotation_x(angle)
        elif channel == "Yrotation":
            axis_rotation = _rotation_y(angle)
        elif channel == "Zrotation":
            axis_rotation = _rotation_z(angle)
        else:
            raise ValueError(f"unsupported BVH rotation channel {channel!r}")
        rotation = _mat_mul(rotation, axis_rotation)
    return rotation


def _write_trc(
    path: str | Path,
    *,
    source_name: str,
    data_rate: float,
    frame_time: float,
    marker_names: tuple[str, ...],
    positions_by_frame: list[dict[str, tuple[float, float, float]]],
    units: str,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = len(positions_by_frame)
    marker_count = len(marker_names)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"PathFileType\t4\t(X/Y/Z)\t{source_name}\n")
        handle.write(
            "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\t"
            "OrigDataRate\tOrigDataStartFrame\tOrigNumFrames\n"
        )
        handle.write(
            f"{data_rate:.10g}\t{data_rate:.10g}\t{frame_count}\t{marker_count}\t"
            f"{units}\t{data_rate:.10g}\t1\t{frame_count}\n"
        )
        handle.write("Frame#\tTime")
        for marker in marker_names:
            handle.write(f"\t{marker}\t\t")
        handle.write("\n")
        handle.write("\t")
        for index in range(1, marker_count + 1):
            handle.write(f"\tX{index}\tY{index}\tZ{index}")
        handle.write("\n\n")
        for frame_index, frame_positions in enumerate(positions_by_frame, start=1):
            handle.write(f"{frame_index}\t{(frame_index - 1) * frame_time:.10g}")
            for marker in marker_names:
                x, y, z = frame_positions[marker]
                handle.write(f"\t{x:.10g}\t{y:.10g}\t{z:.10g}")
            handle.write("\n")


def _identity_matrix() -> tuple[tuple[float, float, float], ...]:
    return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _rotation_x(angle: float) -> tuple[tuple[float, float, float], ...]:
    c = math.cos(angle)
    s = math.sin(angle)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _rotation_y(angle: float) -> tuple[tuple[float, float, float], ...]:
    c = math.cos(angle)
    s = math.sin(angle)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _rotation_z(angle: float) -> tuple[tuple[float, float, float], ...]:
    c = math.cos(angle)
    s = math.sin(angle)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _mat_mul(
    a: tuple[tuple[float, float, float], ...],
    b: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        tuple(sum(a[row][k] * b[k][col] for k in range(3)) for col in range(3))
        for row in range(3)
    )


def _mat_vec(
    matrix: tuple[tuple[float, float, float], ...],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(sum(matrix[row][k] * vector[k] for k in range(3)) for row in range(3))


def _vec_add(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _rajagopal_virtual_markers(
    joints: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    pelvis = _virtual_pelvis_markers(joints)
    right_axis = _unit(_vec_sub(joints["RightLeg"], joints["LeftLeg"]))
    if _vec_norm(right_axis) == 0:
        right_axis = (0.0, 0.0, 1.0)

    return {
        "RACR": joints["RightShoulder"],
        "LACR": joints["LeftShoulder"],
        "C7": _lerp(joints["Neck1"], joints["Neck2"], 0.35),
        "CLAV": _lerp(joints["Chest"], joints["Neck1"], 0.35),
        "RASI": pelvis["RASI"],
        "LASI": pelvis["LASI"],
        "RPSI": pelvis["RPSI"],
        "LPSI": pelvis["LPSI"],
        "RLEL": joints["RightForeArm"],
        "LLEL": joints["LeftForeArm"],
        "RFAradius": joints["RightHand"],
        "LFAradius": joints["LeftHand"],
        "RKJC": joints["RightShin"],
        "LKJC": joints["LeftShin"],
        "RAJC": joints["RightFoot"],
        "LAJC": joints["LeftFoot"],
        "RCAL": _lerp(joints["RightFoot"], joints["RightToeBase"], -0.35),
        "LCAL": _lerp(joints["LeftFoot"], joints["LeftToeBase"], -0.35),
        "RTOE": joints["RightToeBase"],
        "LTOE": joints["LeftToeBase"],
        "RMT5": _vec_add(joints["RightToeBase"], _vec_scale(right_axis, 0.04)),
        "LMT5": _vec_add(joints["LeftToeBase"], _vec_scale(right_axis, -0.04)),
    }


def _adjusted_ulb_virtual_markers(
    joints: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    pelvis = _virtual_pelvis_markers(joints)
    torso_right = _unit(_vec_sub(joints["RightShoulder"], joints["LeftShoulder"]))
    torso_up = _unit(_vec_sub(joints["Neck1"], joints["Chest"]))
    torso_forward = _unit(_cross(torso_right, torso_up))
    if _vec_norm(torso_right) == 0:
        torso_right = _unit(_vec_sub(joints["RightLeg"], joints["LeftLeg"]))
    if _vec_norm(torso_right) == 0:
        torso_right = (1.0, 0.0, 0.0)
    if _vec_norm(torso_forward) == 0:
        torso_forward = (0.0, 0.0, 1.0)
    torso_back = _vec_scale(torso_forward, -1.0)

    return {
        "STRN": _lerp(joints["Chest"], joints["Neck1"], 0.25),
        "RSHO": joints["RightShoulder"],
        "LSHO": joints["LeftShoulder"],
        "C7": _vec_add(
            _lerp(joints["Neck1"], joints["Neck2"], 0.35),
            _vec_scale(torso_back, 0.06),
        ),
        "T10": _vec_add(
            _lerp(joints["Spine2"], joints["Chest"], 0.35),
            _vec_scale(torso_back, 0.09),
        ),
        "CLAV": _lerp(joints["Chest"], joints["Neck1"], 0.55),
        "RUPA": _lerp(joints["RightArm"], joints["RightForeArm"], 0.5),
        "RELB": joints["RightForeArm"],
        "RFRM": _lerp(joints["RightForeArm"], joints["RightHand"], 0.5),
        "RWRA": _vec_add(joints["RightHand"], _vec_scale(torso_right, 0.025)),
        "RWRB": _vec_add(joints["RightHand"], _vec_scale(torso_right, -0.025)),
        "LUPA": _lerp(joints["LeftArm"], joints["LeftForeArm"], 0.5),
        "LELB": joints["LeftForeArm"],
        "LFRM": _lerp(joints["LeftForeArm"], joints["LeftHand"], 0.5),
        "LWRA": _vec_add(joints["LeftHand"], _vec_scale(torso_right, -0.025)),
        "LWRB": _vec_add(joints["LeftHand"], _vec_scale(torso_right, 0.025)),
        "RASI": pelvis["RASI"],
        "LASI": pelvis["LASI"],
        "RTHI": _lerp(joints["RightLeg"], joints["RightShin"], 0.5),
        "RKNE": joints["RightShin"],
        "LTHI": _lerp(joints["LeftLeg"], joints["LeftShin"], 0.5),
        "LKNE": joints["LeftShin"],
        "LPSI": pelvis["LPSI"],
        "RPSI": pelvis["RPSI"],
        "RANK": joints["RightFoot"],
        "LANK": joints["LeftFoot"],
        "RTOE": joints["RightToeBase"],
        "LTOE": joints["LeftToeBase"],
        "RHEE": _lerp(joints["RightFoot"], joints["RightToeBase"], -0.35),
        "LHEE": _lerp(joints["LeftFoot"], joints["LeftToeBase"], -0.35),
        "LFHD": _head_marker(joints["Head"], torso_right, torso_forward, -1.0, 1.0),
        "RFHD": _head_marker(joints["Head"], torso_right, torso_forward, 1.0, 1.0),
        "LBHD": _head_marker(joints["Head"], torso_right, torso_forward, -1.0, -1.0),
        "RBHD": _head_marker(joints["Head"], torso_right, torso_forward, 1.0, -1.0),
        "RBAK": _vec_add(
            _vec_add(
                _lerp(joints["Spine2"], joints["Chest"], 0.65),
                _vec_scale(torso_back, 0.11),
            ),
            _vec_scale(torso_right, 0.045),
        ),
        "LFIN": joints["LeftHandMiddle2"],
        "RFIN": joints["RightHandMiddle2"],
        "RTIB": _lerp(joints["RightShin"], joints["RightFoot"], 0.5),
        "LTIB": _lerp(joints["LeftShin"], joints["LeftFoot"], 0.5),
    }

def _improved_ulb_virtual_markers(
    joints: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    """Improved ULB markers hardcoded from the aligned OpenSim/SOMA marker mesh."""
    return {
        marker_name: _vec_add(joints[anchor], offset)
        for marker_name, (anchor, offset) in IMPROVED_ULB_MARKER_ANCHORS.items()
    }

def _head_marker(
    center: tuple[float, float, float],
    right_axis: tuple[float, float, float],
    forward_axis: tuple[float, float, float],
    right_sign: float,
    forward_sign: float,
) -> tuple[float, float, float]:
    radius = 0.055
    return _vec_add(
        center,
        _vec_add(
            _vec_scale(right_axis, right_sign * radius),
            _vec_scale(forward_axis, forward_sign * radius),
        ),
    )


def _virtual_pelvis_markers(
    joints: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    center = joints["Hips"]
    right_axis = _unit(_vec_sub(joints["RightLeg"], joints["LeftLeg"]))
    up_axis = _unit(_vec_sub(joints["Chest"], joints["Hips"]))
    forward_axis = _unit(_cross(right_axis, up_axis))
    if _vec_norm(right_axis) == 0:
        right_axis = (0.0, 0.0, 1.0)
    if _vec_norm(forward_axis) == 0:
        forward_axis = (1.0, 0.0, 0.0)

    hip_width = max(_vec_norm(_vec_sub(joints["RightLeg"], joints["LeftLeg"])), 0.18)
    lateral = hip_width * 0.45
    depth = hip_width * 0.22
    return {
        "RASI": _vec_add(center, _vec_add(_vec_scale(right_axis, lateral), _vec_scale(forward_axis, depth))),
        "LASI": _vec_add(center, _vec_add(_vec_scale(right_axis, -lateral), _vec_scale(forward_axis, depth))),
        "RPSI": _vec_add(center, _vec_add(_vec_scale(right_axis, lateral * 0.8), _vec_scale(forward_axis, -depth))),
        "LPSI": _vec_add(center, _vec_add(_vec_scale(right_axis, -lateral * 0.8), _vec_scale(forward_axis, -depth))),
    }


def _lerp(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    t: float,
) -> tuple[float, float, float]:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _vec_sub(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vec_scale(
    vector: tuple[float, float, float],
    scale: float,
) -> tuple[float, float, float]:
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


def _vec_norm(vector: tuple[float, float, float]) -> float:
    return math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = _vec_norm(vector)
    if norm == 0:
        return (0.0, 0.0, 0.0)
    return (vector[0] / norm, vector[1] / norm, vector[2] / norm)


def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )

