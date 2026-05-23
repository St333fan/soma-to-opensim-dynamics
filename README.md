# soma-to-opensim-dynamics

Convert SOMA-X/BONES-SEED `.bvh` motion files into OpenSim marker and motion files.

The current workflow is:

1. Read a SOMA-X/BONES-SEED `.bvh` file.
2. Retarget the BVH skeleton to an improved ULB marker set.
3. Write an OpenSim `.trc` marker trajectory.
4. Write an OpenSim Inverse Kinematics setup XML.
5. Run `opensim-cmd run-tool` to generate a model-coordinate `.mot`.

The longer-term goal is to continue from IK into dynamics and muscle-tendon force
analysis so stiffness can be estimated from motion and force outputs.

## Requirements

- Python 3.9+
- OpenSim 4.5
- An OpenSim model with matching ULB marker names, for example `Adjusted_ULBmodel.osim`
- A SOMA-X/BONES-SEED BVH file

The adjusted ULB model is not committed by default. Put it somewhere local and pass
its path with `--model`, or place it in `models/Adjusted_ULBmodel.osim`.

## Install

From the repository root:

```powershell
python -m pip install -e .
```

Check whether `opensim-cmd` can be found:

```powershell
seed-to-opensim doctor
```

If OpenSim is not on `PATH`, pass the executable explicitly to the example script.
On Windows this is often:

```text
C:\OpenSim 4.5\bin\opensim-cmd.exe
```

## Run The Example

This repo includes one small BVH example:

```text
examples/data/nailing_wall_R_003__A282.bvh
```

Run the improved ULB pipeline:

```powershell
python scripts/run_improved_ulb_example.py `
  --model "C:\path\to\Adjusted_ULBmodel.osim" `
  --opensim-cmd "C:\OpenSim 4.5\bin\opensim-cmd.exe"
```

Expected outputs:

```text
output/example_improved_ulb/
  nailing_wall_R_003__A282_Improved_ULBmodel.trc
  nailing_wall_R_003__A282_Improved_ULBmodel_IK_settings.xml
  nailing_wall_R_003__A282_Improved_ULBmodel_IK.mot
  bvh_rajagopal_ik_ik_marker_errors.sto
```

The same script can run any other SOMA-X BVH:

```powershell
python scripts/run_improved_ulb_example.py `
  --input "C:\path\to\motion.bvh" `
  --model "C:\path\to\Adjusted_ULBmodel.osim" `
  --output-dir "output/my_motion"
```

## CLI Notes

The package also exposes `seed-to-opensim` for lower-level conversion commands.

Convert a BVH directly to an improved ULB `.trc`:

```powershell
seed-to-opensim convert-file `
  --input examples/data/nailing_wall_R_003__A282.bvh `
  --kind bvh-improved-ulb-trc `
  --output output/example.trc
```