from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


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


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _xml_path(path: str | Path) -> str:
    return _xml_text(Path(path))


def _xml_text(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})
