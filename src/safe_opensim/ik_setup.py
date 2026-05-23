from __future__ import annotations

from pathlib import Path


def write_inverse_kinematics_setup(
    path: str | Path,
    *,
    model_file: str | Path,
    marker_file: str | Path,
    output_motion_file: str | Path,
    marker_weights: dict[str, float],
    time_range: tuple[float, float],
    accuracy: float = 1e-5,
) -> Path:
    setup_path = Path(path)
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = Path(output_motion_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    task_xml = "\n".join(
        "                "
        f'<IKMarkerTask name="{marker}">\n'
        "                    <apply>true</apply>\n"
        f"                    <weight>{weight:g}</weight>\n"
        "                </IKMarkerTask>"
        for marker, weight in marker_weights.items()
    )
    setup_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="30000">
    <InverseKinematicsTool name="bvh_rajagopal_ik">
        <results_directory>{output_path.parent}</results_directory>
        <model_file>{Path(model_file)}</model_file>
        <constraint_weight>Inf</constraint_weight>
        <accuracy>{accuracy:g}</accuracy>
        <time_range>{time_range[0]:.10g} {time_range[1]:.10g}</time_range>
        <output_motion_file>{output_path}</output_motion_file>
        <report_errors>true</report_errors>
        <report_marker_locations>false</report_marker_locations>
        <IKTaskSet>
            <objects>
{task_xml}
            </objects>
            <groups />
        </IKTaskSet>
        <marker_file>{Path(marker_file)}</marker_file>
        <coordinate_file>Unassigned</coordinate_file>
    </InverseKinematicsTool>
</OpenSimDocument>
""",
        encoding="utf-8",
    )
    return setup_path
