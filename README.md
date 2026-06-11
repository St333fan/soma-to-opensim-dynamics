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

The adjusted ULB model is not committed by default. It comes from the SimTK
project [Analysis of arm swing during human walking](https://simtk.org/projects/arm_swing).
Put `Adjusted_ULBmodel.osim` somewhere local and pass its path with `--model`,
or place it in `models/Adjusted_ULBmodel.osim`.

## Install

From the repository root:

```powershell
python -m pip install -e .
```

If the package is not installed, you can still run the scripts from the repo by
setting `PYTHONPATH` to `src`:

```powershell
$env:PYTHONPATH = "src"
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

This workflow does not require Docker. On Windows, a typical local setup is:

```text
Python:  C:\Users\<you>\miniconda3\python.exe
OpenSim: C:\OpenSim 4.5\bin\opensim-cmd.exe
Code:    this repository, loaded with PYTHONPATH=src if not installed
```

## Run The Example

This repo includes one small BVH example:

```text
examples/data/nailing_wall_R_003__A282.bvh
```

Run the improved ULB pipeline to create both an OpenSim marker file (`.trc`) and
an inverse-kinematics motion file (`.mot`):

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

The `.trc` contains marker trajectories. The `.mot` contains model coordinates
from OpenSim Inverse Kinematics and is the file to load when you want to animate
the model motion in OpenSim.

If `python` is not available on `PATH`, use the full Miniconda Python path:

```powershell
$env:PYTHONPATH = "src"
C:\Users\<you>\miniconda3\python.exe scripts\run_improved_ulb_example.py `
  --input examples\data\nailing_wall_R_003__A282.bvh `
  --model models\Adjusted_ULBmodel.osim `
  --opensim-cmd "C:\OpenSim 4.5\bin\opensim-cmd.exe" `
  --output-dir output\nailing_example
```

The same script can run any other SOMA-X BVH:

```powershell
python scripts/run_improved_ulb_example.py `
  --input "C:\path\to\motion.bvh" `
  --model "C:\path\to\Adjusted_ULBmodel.osim" `
  --output-dir "output/my_motion"
```

For example, to run a taxi-wave BVH and generate a `.trc` plus `.mot`:

```powershell
$env:PYTHONPATH = "src"
C:\Users\<you>\miniconda3\python.exe scripts\run_improved_ulb_example.py `
  --input "C:\path\to\steet_taxi_wave_002__A424.bvh" `
  --model models\Adjusted_ULBmodel.osim `
  --opensim-cmd "C:\OpenSim 4.5\bin\opensim-cmd.exe" `
  --output-dir output\taxi_wave
```

The output directory will contain files like:

```text
taxi_wave/
  steet_taxi_wave_002__A424_Improved_ULBmodel.trc
  steet_taxi_wave_002__A424_Improved_ULBmodel_IK_settings.xml
  steet_taxi_wave_002__A424_Improved_ULBmodel_IK.mot
  bvh_rajagopal_ik_ik_marker_errors.sto
```

If OpenSim reports that it cannot associate a motion with the current model,
make sure the same `.osim` model used with `--model` is open in the GUI before
loading the generated `_IK.mot`.

## Static Optimization

After generating an IK `.mot`, you can write and optionally run a Static
Optimization setup XML. The command below mirrors the important GUI settings:

- `--analyze-every` is the "Analyze every N step(s)" field.
- `--filter-coordinates` enables the "Filter coordinates" checkbox.
- `--coordinate-filter-cutoff` is the cutoff frequency in Hz.

Example:

```powershell
$env:PYTHONPATH = "src"
C:\Users\<you>\miniconda3\python.exe -m safe_opensim static-optimization `
  --model models\Adjusted_ULBmodel.osim `
  --coordinates-file output\taxi_wave\steet_taxi_wave_002__A424_Improved_ULBmodel_IK.mot `
  --setup-output output\taxi_wave_static_optimization\static_optimization_setup.xml `
  --results-dir output\taxi_wave_static_optimization `
  --time-start 0 `
  --time-end 4.574817 `
  --analyze-every 5 `
  --filter-coordinates `
  --coordinate-filter-cutoff 4 `
  --write-states-for-muscle-analysis `
  --opensim-cmd "C:\OpenSim 4.5\bin\opensim-cmd.exe" `
  --run
```

If you only want to create the setup XML without running OpenSim, omit `--run`.
For models with few muscles, lock unused coordinates or add reserve actuators so
Static Optimization has enough forces for the unlocked degrees of freedom.

### States For Muscle Analysis

Static Optimization writes activation, force, and controls files. Add
`--write-states-for-muscle-analysis` if you also want the CLI to create the
states trajectory needed for OpenSim Muscle Analysis.

With that flag, the CLI runs this workflow:

1. Run Static Optimization from the IK `.mot`.
2. Run an OpenSim `StatesReporter` analysis on the same `.mot`.
3. Merge the Static Optimization activation `.sto` into the matching
   `/forceset/<muscle>/activation` columns of the states file.
4. Use the merged states file as the input states file for Muscle Analysis.

For the taxi-wave test, all inputs and outputs were kept in one folder:

```text
output/taxi_wave_static_optimization_without_BRA_ANC_PT_TRIlat_TRImed_BICshort_combined/
  steet_taxi_wave_002__A424_Improved_ULBmodel_IK.mot
  static_optimization_setup.xml
  static_optimization_StaticOptimization_activation.sto
  static_optimization_StaticOptimization_force.sto
  static_optimization_StaticOptimization_controls.xml
  states_reporter_setup.xml
  states_reporter_StatesReporter_states.sto
  states_with_static_optimization_activations.sto
```

Use `states_with_static_optimization_activations.sto` for Muscle Analysis. The
plain `states_reporter_StatesReporter_states.sto` contains the replayed model
states, but its muscle activations are not the Static Optimization solution.

## CLI Notes

The package also exposes `seed-to-opensim` for lower-level conversion commands.

Convert a BVH directly to an improved ULB `.trc`:

```powershell
seed-to-opensim convert-file `
  --input examples/data/nailing_wall_R_003__A282.bvh `
  --kind bvh-improved-ulb-trc `
  --output output/example.trc
```
