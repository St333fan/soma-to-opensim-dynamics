from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from safe_opensim.converters import (
    TRC_MARKER_SETS,
    convert_bvh_to_adjusted_ulb_trc,
    convert_bvh_to_improved_ulb_trc,
    convert_bvh_to_storage,
    convert_bvh_to_trc,
    convert_bvh_to_rajagopal_trc,
    convert_g1_csv_to_storage,
)


class ConverterTests(unittest.TestCase):
    def test_g1_csv_to_mot_generates_time_and_degrees(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "motion.csv"
            output = temp / "motion.mot"
            source.write_text(
                "frame,left_hip_pitch,root_x\n"
                "0,0.0,1.0\n"
                f"1,{math.pi / 2},2.0\n",
                encoding="utf-8",
            )

            result = convert_g1_csv_to_storage(source, output, fps=120)

            self.assertEqual(result.rows, 2)
            text = output.read_text(encoding="utf-8")
            self.assertIn("inDegrees=yes\n", text)
            self.assertIn("time\tleft_hip_pitch\troot_x\n", text)
            self.assertIn("0.008333333333\t90\t2", text)

    def test_g1_csv_column_map_can_rename_and_skip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "motion.csv"
            output = temp / "motion.mot"
            source.write_text("time,a,b\n0,1,2\n", encoding="utf-8")

            result = convert_g1_csv_to_storage(
                source,
                output,
                column_map={"a": "hip_flexion_l", "b": None},
                input_angle_unit="degrees",
                output_angle_unit="degrees",
            )

            self.assertEqual(result.labels, ("time", "hip_flexion_l"))
            self.assertNotIn("\tb\n", output.read_text(encoding="utf-8"))

    def test_bvh_to_mot_exports_channels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "tiny.bvh"
            output = temp / "tiny.mot"
            source.write_text(
                "\n".join(
                    [
                        "HIERARCHY",
                        "ROOT Hips",
                        "{",
                        "  OFFSET 0 0 0",
                        "  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation",
                        "}",
                        "MOTION",
                        "Frames: 2",
                        "Frame Time: 0.01",
                        "1 2 3 10 20 30",
                        "4 5 6 40 50 60",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = convert_bvh_to_storage(source, output, linear_scale=0.01)

            self.assertEqual(result.rows, 2)
            text = output.read_text(encoding="utf-8")
            self.assertIn("time\tHips_Xposition\tHips_Yposition\tHips_Zposition", text)
            self.assertIn("0\t0.01\t0.02\t0.03\t10\t20\t30", text)

    def test_bvh_to_trc_exports_joint_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "tiny.bvh"
            output = temp / "tiny.trc"
            source.write_text(
                "\n".join(
                    [
                        "HIERARCHY",
                        "ROOT Root",
                        "{",
                        "  OFFSET 0 0 0",
                        "  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation",
                        "  JOINT Child",
                        "  {",
                        "    OFFSET 10 0 0",
                        "    CHANNELS 3 Zrotation Xrotation Yrotation",
                        "  }",
                        "}",
                        "MOTION",
                        "Frames: 1",
                        "Frame Time: 0.01",
                        "1 2 3 0 0 0 0 0 0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = convert_bvh_to_trc(source, output, marker_scale=0.01, units="m")

            self.assertEqual(result.frames, 1)
            self.assertEqual(result.markers, 2)
            text = output.read_text(encoding="utf-8")
            self.assertIn("NumFrames\tNumMarkers\tUnits", text)
            self.assertIn("Root\t\t\tChild", text)
            self.assertIn("1\t0\t0.01\t0.02\t0.03\t0.11\t0.02\t0.03", text)
            self.assertIn("\n\n1\t0\t", text)

    def test_bvh_to_rajagopal_trc_exports_model_marker_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "tiny.bvh"
            output = temp / "rajagopal.trc"
            source.write_text(
                "\n".join(
                    [
                        "HIERARCHY",
                        "ROOT Root",
                        "{",
                        "  OFFSET 0 0 0",
                        "  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation",
                        "  JOINT Hips",
                        "  {",
                        "    OFFSET 0 100 0",
                        "    CHANNELS 3 Zrotation Xrotation Yrotation",
                        "    JOINT Chest",
                        "    {",
                        "      OFFSET 0 50 0",
                        "      CHANNELS 3 Zrotation Xrotation Yrotation",
                        "      JOINT Neck1",
                        "      {",
                        "        OFFSET 0 20 0",
                        "        CHANNELS 3 Zrotation Xrotation Yrotation",
                        "        JOINT Neck2",
                        "        {",
                        "          OFFSET 0 10 0",
                        "          CHANNELS 3 Zrotation Xrotation Yrotation",
                        "        }",
                        "      }",
                        "      JOINT RightShoulder",
                        "      {",
                        "        OFFSET 0 10 20",
                        "        CHANNELS 3 Zrotation Xrotation Yrotation",
                        "        JOINT RightForeArm",
                        "        {",
                        "          OFFSET 0 -30 0",
                        "          CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          JOINT RightHand",
                        "          {",
                        "            OFFSET 0 -25 0",
                        "            CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          }",
                        "        }",
                        "      }",
                        "      JOINT LeftShoulder",
                        "      {",
                        "        OFFSET 0 10 -20",
                        "        CHANNELS 3 Zrotation Xrotation Yrotation",
                        "        JOINT LeftForeArm",
                        "        {",
                        "          OFFSET 0 -30 0",
                        "          CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          JOINT LeftHand",
                        "          {",
                        "            OFFSET 0 -25 0",
                        "            CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          }",
                        "        }",
                        "      }",
                        "    }",
                        "    JOINT RightLeg",
                        "    {",
                        "      OFFSET 0 -10 10",
                        "      CHANNELS 3 Zrotation Xrotation Yrotation",
                        "      JOINT RightShin",
                        "      {",
                        "        OFFSET 0 -45 0",
                        "        CHANNELS 3 Zrotation Xrotation Yrotation",
                        "        JOINT RightFoot",
                        "        {",
                        "          OFFSET 0 -45 0",
                        "          CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          JOINT RightToeBase",
                        "          {",
                        "            OFFSET 20 0 0",
                        "            CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          }",
                        "        }",
                        "      }",
                        "    }",
                        "    JOINT LeftLeg",
                        "    {",
                        "      OFFSET 0 -10 -10",
                        "      CHANNELS 3 Zrotation Xrotation Yrotation",
                        "      JOINT LeftShin",
                        "      {",
                        "        OFFSET 0 -45 0",
                        "        CHANNELS 3 Zrotation Xrotation Yrotation",
                        "        JOINT LeftFoot",
                        "        {",
                        "          OFFSET 0 -45 0",
                        "          CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          JOINT LeftToeBase",
                        "          {",
                        "            OFFSET 20 0 0",
                        "            CHANNELS 3 Zrotation Xrotation Yrotation",
                        "          }",
                        "        }",
                        "      }",
                        "    }",
                        "  }",
                        "}",
                        "MOTION",
                        "Frames: 1",
                        "Frame Time: 0.01",
                        " ".join(["0"] * 60),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = convert_bvh_to_rajagopal_trc(source, output)

            self.assertEqual(result.markers, 22)
            text = output.read_text(encoding="utf-8")
            self.assertIn("RACR", text)
            self.assertIn("RASI", text)
            self.assertIn("RTOE", text)

    def test_bvh_to_adjusted_ulb_trc_exports_model_marker_names(self) -> None:
        source = Path(__file__).parents[1] / "nailing_wall_R_003__A282.bvh"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "adjusted_ulb.trc"

            result = convert_bvh_to_adjusted_ulb_trc(source, output)

            self.assertEqual(result.markers, 39)
            self.assertEqual(result.marker_names[0], "STRN")
            self.assertIn("RSHO", result.marker_names)
            self.assertIn("LFIN", result.marker_names)
            text = output.read_text(encoding="utf-8")
            self.assertIn("NumFrames\tNumMarkers\tUnits", text)
            self.assertIn("Frame#\tTime\tSTRN", text)
            self.assertIn("\tRTIB\t\t\tLTIB", text)

    def test_improved_ulb_marker_set_is_registered(self) -> None:
        self.assertIn("improved_ulb", TRC_MARKER_SETS)
        self.assertEqual(TRC_MARKER_SETS["improved_ulb"]["STRN"], 1.0)
        self.assertEqual(TRC_MARKER_SETS["improved_ulb"]["RUPA"], 0.5)

    def test_improved_ulb_exports_hardcoded_marker_names(self) -> None:
        source = Path(__file__).parents[1] / "nailing_wall_R_003__A282.bvh"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "improved_ulb.trc"

            result = convert_bvh_to_improved_ulb_trc(source, output)

            self.assertEqual(result.markers, 39)
            self.assertEqual(result.marker_names, tuple(TRC_MARKER_SETS["improved_ulb"]))
            self.assertIn("Frame#\tTime\tSTRN", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

