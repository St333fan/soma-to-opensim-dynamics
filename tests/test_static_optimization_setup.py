from __future__ import annotations

import shutil
import unittest
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from safe_opensim.static_optimization_setup import (
    merge_static_optimization_activations_into_states,
    write_muscle_analysis_setup,
    write_static_optimization_setup,
    write_states_reporter_setup,
)


class StaticOptimizationSetupTests(unittest.TestCase):
    def test_writes_step_interval_and_coordinate_filter(self) -> None:
        with workspace_temp_dir() as temp:
            setup = write_static_optimization_setup(
                temp / "static_optimization.xml",
                model_file=temp / "model.osim",
                coordinates_file=temp / "motion.mot",
                results_directory=temp / "results",
                time_range=(0.0, 1.5),
                analyze_every=5,
                filter_coordinates=True,
                coordinate_filter_cutoff=4.0,
            )

            text = setup.read_text(encoding="utf-8")
            self.assertIn("<StaticOptimization name=\"StaticOptimization\">", text)
            self.assertIn("<step_interval>5</step_interval>", text)
            self.assertIn("<lowpass_cutoff_frequency_for_coordinates>4</lowpass_cutoff_frequency_for_coordinates>", text)
            self.assertIn("<initial_time>0</initial_time>", text)
            self.assertIn("<final_time>1.5</final_time>", text)

    def test_coordinate_filter_is_off_by_default(self) -> None:
        with workspace_temp_dir() as temp:
            setup = write_static_optimization_setup(
                temp / "static_optimization.xml",
                model_file=temp / "model.osim",
                coordinates_file=temp / "motion.mot",
                results_directory=temp / "results",
                time_range=(0.0, 1.0),
            )

            text = setup.read_text(encoding="utf-8")
            self.assertIn("<step_interval>1</step_interval>", text)
            self.assertIn("<lowpass_cutoff_frequency_for_coordinates>-1</lowpass_cutoff_frequency_for_coordinates>", text)

    def test_analyze_every_must_be_positive(self) -> None:
        with workspace_temp_dir() as temp:
            with self.assertRaises(ValueError):
                write_static_optimization_setup(
                    temp / "static_optimization.xml",
                    model_file=temp / "model.osim",
                    coordinates_file=temp / "motion.mot",
                    results_directory=temp / "results",
                    time_range=(0.0, 1.0),
                    analyze_every=0,
                )

    def test_writes_states_reporter_setup(self) -> None:
        with workspace_temp_dir() as temp:
            setup = write_states_reporter_setup(
                temp / "states_reporter_setup.xml",
                model_file=temp / "model.osim",
                coordinates_file=temp / "motion.mot",
                results_directory=temp / "results",
                time_range=(0.0, 2.0),
                analyze_every=3,
                filter_coordinates=True,
                coordinate_filter_cutoff=4.0,
            )

            text = setup.read_text(encoding="utf-8")
            self.assertIn("<AnalyzeTool name=\"states_reporter\">", text)
            self.assertIn("<StatesReporter name=\"StatesReporter\">", text)
            self.assertIn("<step_interval>3</step_interval>", text)
            self.assertIn("<lowpass_cutoff_frequency_for_coordinates>4</lowpass_cutoff_frequency_for_coordinates>", text)

    def test_merges_static_optimization_activations_into_states(self) -> None:
        with workspace_temp_dir() as temp:
            states_file = temp / "states.sto"
            activation_file = temp / "activation.sto"
            output_file = temp / "merged_states.sto"
            states_file.write_text(
                "\n".join(
                    [
                        "ModelStates",
                        "version=1",
                        "nRows=2",
                        "nColumns=5",
                        "endheader",
                        "time\t/forceset/DELT1/activation\t/forceset/DELT1/fiber_length\t/forceset/BRD/activation\t/forceset/BRD/fiber_length",
                        "0\t0\t1.1\t0\t1.2",
                        "0.1\t0\t1.3\t0\t1.4",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            activation_file.write_text(
                "\n".join(
                    [
                        "Static Optimization",
                        "version=1",
                        "nRows=2",
                        "nColumns=3",
                        "endheader",
                        "time\tDELT1\tBRD",
                        "0\t0.25\t0.75",
                        "0.1\t0.5\t1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            merge_static_optimization_activations_into_states(
                states_file,
                activation_file,
                output_file,
            )

            text = output_file.read_text(encoding="utf-8")
            self.assertIn("StaticOptimization activation columns merged", text)
            self.assertIn("0\t0.25\t1.1\t0.75\t1.2", text)
            self.assertIn("0.1\t0.5\t1.3\t1\t1.4", text)

    def test_writes_muscle_analysis_setup_from_motion_and_controls(self) -> None:
        with workspace_temp_dir() as temp:
            setup = write_muscle_analysis_setup(
                temp / "muscle_analysis_setup.xml",
                model_file=temp / "model.osim",
                coordinates_file=temp / "motion.mot",
                controls_file=temp / "static_optimization_controls.xml",
                results_directory=temp / "results",
                time_range=(0.0, 4.5),
                filter_coordinates=True,
                coordinate_filter_cutoff=4.0,
            )

            text = setup.read_text(encoding="utf-8")
            self.assertIn("<AnalyzeTool name=\"muscle_analysis\">", text)
            self.assertIn("<MuscleAnalysis name=\"MuscleAnalysis\">", text)
            self.assertIn("<solve_for_equilibrium_for_auxiliary_states>true</solve_for_equilibrium_for_auxiliary_states>", text)
            self.assertIn("<controls_file>", text)
            self.assertIn("static_optimization_controls.xml</controls_file>", text)
            self.assertIn("<states_file />", text)
            self.assertIn("motion.mot</coordinates_file>", text)
            self.assertIn("<lowpass_cutoff_frequency_for_coordinates>4</lowpass_cutoff_frequency_for_coordinates>", text)


@contextmanager
def workspace_temp_dir() -> Iterator[Path]:
    path = Path("output") / "unit_test_tmp" / uuid.uuid4().hex
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


if __name__ == "__main__":
    unittest.main()
