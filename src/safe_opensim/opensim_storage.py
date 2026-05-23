from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from pathlib import Path


_UNSAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9_./:-]+")


def sanitize_label(label: str) -> str:
    """Return a conservative OpenSim storage column label."""
    cleaned = _UNSAFE_LABEL_RE.sub("_", label.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unnamed"


def format_storage_number(value: float) -> str:
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return f"{value:.10g}"


def write_storage(
    path: str | Path,
    *,
    name: str,
    labels: Sequence[str],
    rows: Iterable[Sequence[float]],
    in_degrees: bool | None,
) -> int:
    """Write an OpenSim .mot/.sto-style storage file and return row count."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    materialized_rows = list(rows)
    expected_width = len(labels)
    for row_index, row in enumerate(materialized_rows, start=1):
        if len(row) != expected_width:
            raise ValueError(
                f"row {row_index} has {len(row)} columns, expected {expected_width}"
            )

    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{name}\n")
        handle.write("version=1\n")
        handle.write(f"nRows={len(materialized_rows)}\n")
        handle.write(f"nColumns={len(labels)}\n")
        if in_degrees is not None:
            handle.write(f"inDegrees={'yes' if in_degrees else 'no'}\n")
        handle.write("endheader\n")
        handle.write("\t".join(labels))
        handle.write("\n")
        for row in materialized_rows:
            handle.write("\t".join(format_storage_number(float(value)) for value in row))
            handle.write("\n")

    return len(materialized_rows)
