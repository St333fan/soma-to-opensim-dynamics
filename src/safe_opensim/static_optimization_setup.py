from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

STATIC_OPTIMIZATION_ACTIVATION_FILENAME = (
    "static_optimization_StaticOptimization_activation.sto"
)
STATIC_OPTIMIZATION_CONTROLS_FILENAME = (
    "static_optimization_StaticOptimization_controls.xml"
)
STATES_REPORTER_SETUP_FILENAME = "states_reporter_setup.xml"
STATES_REPORTER_STATES_FILENAME = "states_reporter_StatesReporter_states.sto"
MERGED_STATES_FILENAME = "states_with_static_optimization_activations.sto"
MUSCLE_ANALYSIS_SETUP_FILENAME = "muscle_analysis_setup.xml"


def write_static_optimization_setup(
    path: str | Path,
    *,
    model_file: str | Path,
    coordinates_file: str | Path,
    results_directory: str | Path,
    time_range: tuple[float, float],
    analyze_every: int = 1,
    filter_coordinates: bool = False,
    coordinate_filter_cutoff: float = 4.0,
    external_loads_file: str | Path | None = None,
    activation_exponent: float = 2.0,
    use_muscle_physiology: bool = True,
    use_model_force_set: bool = True,
    optimizer_convergence_criterion: float = 1e-4,
    optimizer_max_iterations: int = 100,
) -> Path:
    """Write an OpenSim AnalyzeTool setup containing StaticOptimization.

    ``analyze_every`` maps to StaticOptimization's ``step_interval`` property,
    the "Analyze every N step(s)" field in the OpenSim GUI.
    """

    if analyze_every < 1:
        raise ValueError("analyze_every must be at least 1")
    if optimizer_max_iterations < 1:
        raise ValueError("optimizer_max_iterations must be at least 1")
    if filter_coordinates and coordinate_filter_cutoff <= 0:
        raise ValueError("coordinate_filter_cutoff must be positive when filtering")

    setup_path = Path(path)
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    results_path = Path(results_directory)
    results_path.mkdir(parents=True, exist_ok=True)

    external_loads = "" if external_loads_file is None else str(Path(external_loads_file))
    lowpass_cutoff_frequency = coordinate_filter_cutoff if filter_coordinates else -1.0

    setup_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500">
    <AnalyzeTool name="static_optimization">
        <model_file>{_xml_path(model_file)}</model_file>
        <replace_force_set>false</replace_force_set>
        <force_set_files />
        <results_directory>{_xml_text(results_path)}</results_directory>
        <output_precision>8</output_precision>
        <initial_time>{time_range[0]:.10g}</initial_time>
        <final_time>{time_range[1]:.10g}</final_time>
        <solve_for_equilibrium_for_auxiliary_states>false</solve_for_equilibrium_for_auxiliary_states>
        <maximum_number_of_integrator_steps>20000</maximum_number_of_integrator_steps>
        <maximum_integrator_step_size>1</maximum_integrator_step_size>
        <minimum_integrator_step_size>1e-08</minimum_integrator_step_size>
        <integrator_error_tolerance>1e-05</integrator_error_tolerance>
        <AnalysisSet name="Analyses">
            <objects>
                <StaticOptimization name="StaticOptimization">
                    <on>true</on>
                    <start_time>{time_range[0]:.10g}</start_time>
                    <end_time>{time_range[1]:.10g}</end_time>
                    <step_interval>{analyze_every}</step_interval>
                    <in_degrees>true</in_degrees>
                    <use_model_force_set>{_bool(use_model_force_set)}</use_model_force_set>
                    <activation_exponent>{activation_exponent:g}</activation_exponent>
                    <use_muscle_physiology>{_bool(use_muscle_physiology)}</use_muscle_physiology>
                    <optimizer_convergence_criterion>{optimizer_convergence_criterion:g}</optimizer_convergence_criterion>
                    <optimizer_max_iterations>{optimizer_max_iterations}</optimizer_max_iterations>
                </StaticOptimization>
            </objects>
            <groups />
        </AnalysisSet>
        <ControllerSet name="Controllers">
            <components />
            <objects />
            <groups />
        </ControllerSet>
        <external_loads_file>{_xml_text(external_loads)}</external_loads_file>
        <states_file />
        <coordinates_file>{_xml_path(coordinates_file)}</coordinates_file>
        <speeds_file />
        <lowpass_cutoff_frequency_for_coordinates>{lowpass_cutoff_frequency:g}</lowpass_cutoff_frequency_for_coordinates>
    </AnalyzeTool>
</OpenSimDocument>
""",
        encoding="utf-8",
    )
    return setup_path


def write_states_reporter_setup(
    path: str | Path,
    *,
    model_file: str | Path,
    coordinates_file: str | Path,
    results_directory: str | Path,
    time_range: tuple[float, float],
    analyze_every: int = 1,
    filter_coordinates: bool = False,
    coordinate_filter_cutoff: float = 4.0,
    external_loads_file: str | Path | None = None,
) -> Path:
    """Write an OpenSim AnalyzeTool setup containing StatesReporter."""

    if analyze_every < 1:
        raise ValueError("analyze_every must be at least 1")
    if filter_coordinates and coordinate_filter_cutoff <= 0:
        raise ValueError("coordinate_filter_cutoff must be positive when filtering")

    setup_path = Path(path)
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    results_path = Path(results_directory)
    results_path.mkdir(parents=True, exist_ok=True)

    external_loads = "" if external_loads_file is None else str(Path(external_loads_file))
    lowpass_cutoff_frequency = coordinate_filter_cutoff if filter_coordinates else -1.0

    setup_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500">
    <AnalyzeTool name="states_reporter">
        <model_file>{_xml_path(model_file)}</model_file>
        <replace_force_set>false</replace_force_set>
        <force_set_files />
        <results_directory>{_xml_text(results_path)}</results_directory>
        <output_precision>8</output_precision>
        <initial_time>{time_range[0]:.10g}</initial_time>
        <final_time>{time_range[1]:.10g}</final_time>
        <solve_for_equilibrium_for_auxiliary_states>false</solve_for_equilibrium_for_auxiliary_states>
        <maximum_number_of_integrator_steps>20000</maximum_number_of_integrator_steps>
        <maximum_integrator_step_size>1</maximum_integrator_step_size>
        <minimum_integrator_step_size>1e-08</minimum_integrator_step_size>
        <integrator_error_tolerance>1e-05</integrator_error_tolerance>
        <AnalysisSet name="Analyses">
            <objects>
                <StatesReporter name="StatesReporter">
                    <on>true</on>
                    <start_time>{time_range[0]:.10g}</start_time>
                    <end_time>{time_range[1]:.10g}</end_time>
                    <step_interval>{analyze_every}</step_interval>
                    <in_degrees>true</in_degrees>
                </StatesReporter>
            </objects>
            <groups />
        </AnalysisSet>
        <ControllerSet name="Controllers">
            <components />
            <objects />
            <groups />
        </ControllerSet>
        <external_loads_file>{_xml_text(external_loads)}</external_loads_file>
        <states_file />
        <coordinates_file>{_xml_path(coordinates_file)}</coordinates_file>
        <speeds_file />
        <lowpass_cutoff_frequency_for_coordinates>{lowpass_cutoff_frequency:g}</lowpass_cutoff_frequency_for_coordinates>
    </AnalyzeTool>
</OpenSimDocument>
""",
        encoding="utf-8",
    )
    return setup_path


def write_muscle_analysis_setup(
    path: str | Path,
    *,
    model_file: str | Path,
    coordinates_file: str | Path,
    controls_file: str | Path,
    results_directory: str | Path,
    time_range: tuple[float, float],
    filter_coordinates: bool = False,
    coordinate_filter_cutoff: float = 4.0,
    external_loads_file: str | Path | None = None,
    analyze_every: int = 1,
    solve_for_equilibrium: bool = True,
    muscle_list: str = "all",
    moment_arm_coordinate_list: str = "all",
    compute_moments: bool = True,
) -> Path:
    """Write an OpenSim AnalyzeTool setup containing MuscleAnalysis.

    This intentionally uses ``coordinates_file`` instead of ``states_file`` so
    OpenSim's coordinate filter applies, matching the Analyze Tool GUI motion
    input workflow.
    """

    if analyze_every < 1:
        raise ValueError("analyze_every must be at least 1")
    if filter_coordinates and coordinate_filter_cutoff <= 0:
        raise ValueError("coordinate_filter_cutoff must be positive when filtering")

    setup_path = Path(path)
    setup_path.parent.mkdir(parents=True, exist_ok=True)
    results_path = Path(results_directory)
    results_path.mkdir(parents=True, exist_ok=True)

    external_loads = "" if external_loads_file is None else str(Path(external_loads_file))
    lowpass_cutoff_frequency = coordinate_filter_cutoff if filter_coordinates else -1.0

    setup_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500">
    <AnalyzeTool name="muscle_analysis">
        <model_file>{_xml_path(model_file)}</model_file>
        <replace_force_set>false</replace_force_set>
        <force_set_files />
        <results_directory>{_xml_text(results_path)}</results_directory>
        <output_precision>8</output_precision>
        <initial_time>{time_range[0]:.10g}</initial_time>
        <final_time>{time_range[1]:.10g}</final_time>
        <solve_for_equilibrium_for_auxiliary_states>{_bool(solve_for_equilibrium)}</solve_for_equilibrium_for_auxiliary_states>
        <maximum_number_of_integrator_steps>20000</maximum_number_of_integrator_steps>
        <maximum_integrator_step_size>1</maximum_integrator_step_size>
        <minimum_integrator_step_size>1e-08</minimum_integrator_step_size>
        <integrator_error_tolerance>1e-05</integrator_error_tolerance>
        <AnalysisSet name="Analyses">
            <objects>
                <MuscleAnalysis name="MuscleAnalysis">
                    <on>true</on>
                    <start_time>{time_range[0]:.10g}</start_time>
                    <end_time>{time_range[1]:.10g}</end_time>
                    <step_interval>{analyze_every}</step_interval>
                    <in_degrees>true</in_degrees>
                    <muscle_list>{_xml_text(muscle_list)}</muscle_list>
                    <moment_arm_coordinate_list>{_xml_text(moment_arm_coordinate_list)}</moment_arm_coordinate_list>
                    <compute_moments>{_bool(compute_moments)}</compute_moments>
                </MuscleAnalysis>
            </objects>
            <groups />
        </AnalysisSet>
        <ControllerSet name="Controllers">
            <objects>
                <ControlSetController name="StaticOptimizationControls">
                    <actuator_list />
                    <isDisabled>false</isDisabled>
                    <controls_file>{_xml_path(controls_file)}</controls_file>
                </ControlSetController>
            </objects>
            <groups />
        </ControllerSet>
        <external_loads_file>{_xml_text(external_loads)}</external_loads_file>
        <states_file />
        <coordinates_file>{_xml_path(coordinates_file)}</coordinates_file>
        <speeds_file />
        <lowpass_cutoff_frequency_for_coordinates>{lowpass_cutoff_frequency:g}</lowpass_cutoff_frequency_for_coordinates>
    </AnalyzeTool>
</OpenSimDocument>
""",
        encoding="utf-8",
    )
    return setup_path


def merge_static_optimization_activations_into_states(
    states_file: str | Path,
    activation_file: str | Path,
    output_file: str | Path,
) -> Path:
    """Merge Static Optimization activations into an OpenSim states file.

    OpenSim's StatesReporter writes muscle activation state columns, but those
    columns are not populated with Static Optimization's activation solution.
    This copies matching activation columns from ``activation_file`` into
    ``/forceset/<muscle>/activation`` columns in ``states_file``.
    """

    states = _read_storage(states_file)
    activations = _read_storage(activation_file)
    if len(states.rows) != len(activations.rows):
        raise ValueError(
            "states and activation files must have the same number of rows "
            f"({len(states.rows)} != {len(activations.rows)})"
        )

    state_columns = {column: index for index, column in enumerate(states.columns)}
    activation_columns = {
        column: index for index, column in enumerate(activations.columns)
    }

    merged = 0
    for muscle in activations.columns[1:]:
        state_column = f"/forceset/{muscle}/activation"
        state_index = state_columns.get(state_column)
        if state_index is None:
            continue

        activation_index = activation_columns[muscle]
        for state_row, activation_row in zip(states.rows, activations.rows):
            state_row[state_index] = activation_row[activation_index]
        merged += 1

    if merged == 0:
        raise ValueError("no matching muscle activation state columns were found")

    header = list(states.header)
    endheader_index = header.index("endheader")
    header.insert(
        endheader_index,
        "This copy has StaticOptimization activation columns merged into the model state activation paths.",
    )

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(header + ["\t".join(states.columns)] + ["\t".join(row) for row in states.rows])
        + "\n",
        encoding="utf-8",
    )
    return output_path


class _Storage:
    def __init__(self, header: list[str], columns: list[str], rows: list[list[str]]) -> None:
        self.header = header
        self.columns = columns
        self.rows = rows


def _read_storage(path: str | Path) -> _Storage:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    try:
        endheader_index = lines.index("endheader")
    except ValueError as exc:
        raise ValueError(f"{path} is missing an endheader line") from exc

    if endheader_index + 1 >= len(lines):
        raise ValueError(f"{path} is missing a column header row")

    header = lines[: endheader_index + 1]
    columns = lines[endheader_index + 1].split("\t")
    rows = [line.split() for line in lines[endheader_index + 2 :] if line.strip()]
    return _Storage(header, columns, rows)


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _xml_path(path: str | Path) -> str:
    return _xml_text(Path(path))


def _xml_text(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})
