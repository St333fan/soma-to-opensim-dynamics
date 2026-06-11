from __future__ import annotations

import shutil
import unittest
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from safe_opensim.static_optimization_setup import write_static_optimization_setup


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
