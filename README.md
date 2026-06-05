# BayIW_Rectan_barotropic — Waves in a Rectangular Bay (Barotropic / Constant Density)

**Master's Degree Thesis Project**

This project uses the [MITgcm](https://mitgcm.org/) ocean general circulation model to simulate the
wind-driven response of a rectangular bay under a **barotropic** configuration: the density is
**constant** throughout the water column (no stratification, **N² = 0**). It serves as the
unstratified reference against which the stratified internal-wave cases are compared:

| Case | Repository | Stratification |
|---|---|---|
| Realistic | `BayIW_Rectan/` | February climatological T/S profiles |
| Linear | `BayIW_Rectan_linear/` | Linearly varying density profile |
| Two-layer | `BayIW_Rectan_2layer/` | Idealized two-layer temperature profile |
| **Barotropic** | **`BayIW_Rectan_barotropic/`** | **Constant density (uniform T, N² = 0)** |

The simulations are run with and without the bay geometry to isolate the bay's influence on the
(barotropic) dynamics.

---

## Project Structure

```
BayIW_Rectan_barotropic/
├── build/                        # MITgcm compilation directory
├── code/                         # Model configuration and size files
│   ├── SIZE.h                    # Grid decomposition parameters
│   ├── packages.conf             # Enabled MITgcm packages
│   ├── OBCS_OPTIONS.h            # Open boundary condition options
│   └── DIAGNOSTICS_SIZE.h        # Diagnostics buffer sizes
├── input/                        # Forcing, bathymetry, and preprocessing scripts
│   ├── *.bin                     # Binary input files (bathymetry, grid spacing, T/S, wind)
│   ├── barotropic_temp/salt_*.bin # Uniform (constant-density) T/S initial condition
│   ├── STATE/                    # Reference state generation scripts
│   ├── *.ipynb                   # Jupyter notebooks for input generation and analysis
│   └── *.py                      # Python utility scripts
├── run_expand/                   # Run directory — with bay geometry
│   ├── data                      # Main model parameter file
│   ├── data.diagnostics          # Diagnostics configuration
│   ├── data.obcs                 # Open boundary condition parameters
│   ├── data.pkg                  # Package switches
│   ├── data.mnc                  # NetCDF output settings
│   └── mnc_*/                    # NetCDF output directories (one per MPI rank)
├── run_expand_nobay/             # Run directory — without bay (control case)
├── compile_and_run_expand.sh     # Script to compile and run both simulations
├── run_expands.sh                # Run-only script (no recompilation)
├── Merge_MPI_STDOUT.sh           # Merge STDOUT files from all MPI ranks
└── compress_nc.sh                # Compress NetCDF output files
```

---

## Model Configuration

| Parameter | Value |
|---|---|
| Model | MITgcm |
| Grid type | Cartesian |
| Horizontal resolution | Variable (expanded grid: 560 × 352 points) |
| Vertical levels | 50 (stretched: 1 m near surface to ~46 m at depth) |
| Time step | 30 s |
| Equation of state | Linear (`tAlpha=2e-4`, `sBeta=0`) |
| Density | **Constant (999.8 kg m⁻³, N² = 0)** |
| Free surface | Implicit |
| Lateral viscosity | 100 m² s⁻¹ |
| Vertical viscosity | 1 × 10⁻⁵ m² s⁻¹ |
| Coriolis parameter (f₀) | 6.97 × 10⁻⁵ s⁻¹ |

### Packages used

| Package | Purpose |
|---|---|
| OBCS | Open boundary conditions (Orlanski radiation + sponge layers) |
| Diagnostics | Output of density anomaly fields (`RHOAnoma`) |
| MNC | NetCDF output |

### Boundary conditions

Open boundaries are applied on the south, west, and east edges using **Orlanski radiation**
conditions. A sponge layer of 10 grid cells damps spurious reflections near the boundaries.
Barotropic velocity balance is applied to maintain mass conservation.

### Forcing

- **Wind**: Periodic meridional wind forcing applied in stage 1 only (period = 1200 s,
  cycle = 216 000 s) (`make_wind_forcing_local.ipynb`)
- **Initial temperature**: Uniform / constant profile → constant density
  (`barotropic_temp_50zlev_560x352.bin`)
- **Initial salinity**: Constant (`barotropic_salt_50zlev_560x352.bin`)

---

## Bay Geometry

The domain features a **rectangular bay** carved into a coastal shelf. The bay geometry is defined
in `input/bahia_rectan_impar_func.ipynb` with the following dimensions:

| Parameter | Value |
|---|---|
| Bay width | ~60 km (from −L/4 to L/4, where L = 119 km) |
| Bay length | ~119 km |
| Bay depth | 164 m (constant, flat bottom) |
| Open ocean depth | ~1000 m |

The domain uses a **variable horizontal grid spacing**: uniform 200 m resolution in the central
region containing the bay, expanding outward to reduce the domain size while minimizing boundary
reflections. The geometry is **identical** to the stratified cases — only the density structure
changes — so that the bay's effect can be compared across stratification scenarios.

---

## Barotropic (Constant Density)

Because the linear equation of state uses `sBeta = 0`, density depends only on temperature:

```
rho = rhoNil * (1 - tAlpha * (T - tRef))
```

For the **barotropic** case the temperature profile is set **uniform** (`T(z) = tRef = 33.6 °C`),
which makes the density **constant** everywhere and the buoyancy frequency **N² = 0**. There is no
density interface, so the system supports **no internal (baroclinic) waves**; the wind forcing
excites only the **barotropic mode**. This case is the natural limit `grad_rho → 0` of the linear
stratification profile and provides a clean unstratified reference for the thesis comparison.

The constant-density initial condition is produced by `input/make_T_S_bin_Tempfunc.ipynb` with
`grad_rho = 0.0`, writing `barotropic_temp/salt_50zlev_560x352.bin`.

---

## Simulation Cases

| Run directory | Bay geometry | Description |
|---|---|---|
| `run_expand/` | With bay | Primary case with rectangular bay bathymetry |
| `run_expand_nobay/` | Without bay | Control case — open coastal domain |

Both cases share the same model executable and physical parameters, and follow the same two-stage
run strategy described below.

### Two-stage run strategy

Each simulation is run in two consecutive stages:

| Stage | `startTime` | `endTime` | `nIter0` | Wind forcing | Purpose |
|---|---|---|---|---|---|
| 1 — Forced | 0 s | 216 000 s (~2.5 days) | 0 | ON (periodic, 1200 s period) | Wind-driven generation |
| 2 — Free | 216 000 s | 432 000 s (~5 days total) | 7200 | OFF | Free propagation and decay after forcing stops |

Stage 1 starts from rest with the uniform (constant-density) T/S initial condition and applies
periodic wind forcing. It writes a checkpoint (`ckptA`) at the end. Stage 2 restarts from that
checkpoint (`pickupSuff='ckptA'`) with the wind forcing commented out.

The `data` files committed to the repository correspond to **stage 2**. To run stage 1, update
`&PARM03` to:
```
startTime=0., endTime=216000., nIter0=0,
periodicExternalForcing=.TRUE., externForcingPeriod=1200., externForcingCycle=216000.,
```
and uncomment the `meridWindFile` and `hydrogThetaFile` lines in `&PARM05`.

---

## Differences from the Linear Stratification Case

| Parameter | Linear (`BayIW_Rectan_linear`) | Barotropic (`BayIW_Rectan_barotropic`) |
|---|---|---|
| Temperature profile | Linearly varying with depth | Uniform (`T = 33.6 °C` at all levels) |
| Density profile | Linear (`d rho/dz = 1.043e-2 kg m⁻⁴`) | Constant (`d rho/dz = 0`) |
| Buoyancy frequency N² | Constant ≈ 1.03 × 10⁻⁴ s⁻² | **0** |
| Internal waves | Present (constant-N modes) | None (barotropic mode only) |
| T/S input files | `linear_temp/salt_50zlev_560x352.bin` | `barotropic_temp/salt_50zlev_560x352.bin` |
| `make_T_S_bin_Tempfunc.ipynb` | `grad_rho = 1.043e-2` | `grad_rho = 0.0` |

Bathymetry (`bahia_rectan_impar_func.ipynb`), grid spacing, wind forcing
(`make_wind_forcing_local.ipynb`), and all model parameters in `data` are **unchanged**.

---

## Input File Generation

The `input/` directory contains Jupyter notebooks used to prepare all binary input files:

| Notebook | Purpose |
|---|---|
| `bahia_rectan_impar_func.ipynb` | Rectangular bay bathymetry generation (unchanged) |
| `make_T_S_bin_Tempfunc.ipynb` | Generate **constant-density** (barotropic) T/S initial condition (`grad_rho = 0`) |
| `make_wind_forcing_local.ipynb` | Generate periodic wind forcing fields (unchanged) |
| `check_output*.ipynb` | Post-processing and visualization of model output |
| `check_output_scenarios_func.ipynb` | Cross-scenario comparison with other stratification cases |

---

## How to Compile and Run

### Requirements

- MITgcm source tree (this directory lives under `MITgcm/verification/`)
- Fortran compiler (`gfortran`)
- MPI (optional, for parallel runs)
- Python 3 with `numpy`, `scipy`, `matplotlib`, `xarray`, `netCDF4` (for preprocessing and analysis)
- Jupyter Notebook

### Compilation and execution

```bash
bash compile_and_run_expand.sh
```

The script will interactively ask whether to:
1. Clean the `build/` directory before compiling
2. Enable MPI compilation
3. Clean run directories before execution
4. Run with MPI (and how many cores)

Both `run_expand/` (with bay) and `run_expand_nobay/` (without bay) are run sequentially.

### Run only (no recompilation)

```bash
bash run_expands.sh
```

### Run a single case

```bash
cd run_expand
bash run_expand.sh
```

Or manually:

```bash
cp ../build/mitgcmuv .
mpirun -np 4 ./mitgcmuv > output.txt
```

### Full 2-stage run on the cluster (SLURM)

`submit_2stage_barotropic.slurm` automates the complete two-stage strategy for both
`run_expand/` (with bay) and `run_expand_nobay/` (control), using the prebuilt MPI executable:

```bash
sbatch submit_2stage_barotropic.slurm
```

It swaps `data.stage1` (forced, 0 → 216 000 s, writes `pickup.ckptA`) and `data.stage2`
(free restart, 216 000 → 432 000 s) in each run directory, checks for `NORMAL END`, and prints
`theta_min/max` after each stage as a barotropic sanity check (should stay 33.6). NetCDF output is
kept in `OUT_stage1/` and `OUT_stage2/`. Compile the model first (see above); the `data.stage1` /
`data.stage2` files live in each run directory.

---

## Output

Model output is written as **NetCDF** files into `mnc_*/` subdirectories (one per MPI rank). The
primary diagnostic field is:

- `diag_rho` — density anomaly (`RHOAnoma`), output every 900 s (15 min). In the barotropic case
  this field should remain ~0 (constant density), serving as a useful sanity check.

### Post-processing utilities

```bash
bash Merge_MPI_STDOUT.sh    # Merge STDOUT logs from all MPI ranks into one file
bash compress_nc.sh         # Compress NetCDF output to reduce disk usage
```

---

## Scientific Context

The barotropic case removes stratification entirely (`N² = 0`). With no density interface the model
supports only the **barotropic (depth-independent) mode**, so the wind forcing cannot generate
internal waves. This makes it the ideal **control / reference** experiment:

1. Isolating the purely barotropic, geometry-driven response of the bay
2. Quantifying, by difference with the stratified cases, the part of the response that is genuinely
   baroclinic (internal-wave) in origin
3. Verifying the numerics: the density anomaly should stay ~0 throughout the run

---

## Author

Esteban Cruz Isidro
