# WRF-WVT multi-tag

Run WRF with **several moisture tracers (tags) at once**. Each tag has its own
source region, and one simulation tracks up to 10 tags (or more, after one
rebuild).

This is an extension of **WRF-WVTs**, the WRF moisture-tracer (water vapor
tracer) code by **Damián Insua-Costa and Gonzalo Miguez-Macho**. WRF-WVTs
tracks moisture from one source region per run; this patch lets one run carry
N tags, each giving exactly what its own single-tag WRF-WVTs run would give.

> **Credit.** The moisture-tracer physics (the tracer versions of WSM6, Kain–Fritsch
> and YSU, the surface source, the 3D source/sink masks) is the work of the
> WRF-WVTs developers, not mine:
> <https://github.com/damianinsua/WRF-WVTs>.
> WRF itself is developed by NCAR and the WRF community: <https://github.com/wrf-model/WRF>.
> This repository contains **only the multi-tag changes**, as a patch on top of
> WRF 4.3.3 + WRF-WVTs. It does not redistribute WRF or WRF-WVTs; get them from
> their own repositories. If you use this, please cite WRF-WVTs:
>
> Insua-Costa, D. and Miguez-Macho, G.: A new moisture tagging capability in the
> Weather Research and Forecasting model: formulation, validation and application
> to the 2014 Great Lake-effect snowstorm, *Earth Syst. Dynam.*, 9, 167–185,
> <https://doi.org/10.5194/esd-9-167-2018>, 2018.

Multi-tag extension: Hadi Zanganeh Kia (University of Houston).

---

## What it does

| | WRF-WVTs | WRF-WVT multi-tag |
|---|---|---|
| tags per run | 1 | 1 to 10 (more after one rebuild) |
| switch | `tracer_opt = 4` | `tracer_opt = 4` (1 tag) or `40 + N` (N tags) |
| masks | `TRMASK` (`TRMASK3D`, `TRMASK3D2`) | the same for tag 1, plus `TRMASK_T2`, `TRMASK_T3`, … |
| output | `qv_tr`, `TR_RAINNC`, … | the same for tag 1, plus `qv_tr_t2`, `TR_RAINNC_T2`, … |

- With `tracer_opt = 4` the model is **bit-for-bit identical** to WRF-WVTs.
- Every tag is independent: a tag never changes the model or another tag, so
  tag *k* of an N-tag run equals a single-tag WRF-WVTs run with that mask
  (verified bit for bit, see [Validation](#validation)).
- Supported physics: the schemes WRF-WVTs supports — WSM6 microphysics
  (`mp_physics = 6`), Kain–Fritsch cumulus (`cu_physics = 1`), YSU PBL
  (`bl_pbl_physics = 1`) — with any surface scheme that sets `QFX`
  (tested with Noah, `sf_surface_physics = 2`).

## Install

You need WRF 4.3.3 and the WRF-WVTs modules, then this patch.

```bash
# 1. WRF 4.3.3
wget https://github.com/wrf-model/WRF/archive/refs/tags/v4.3.3.tar.gz
tar xzf v4.3.3.tar.gz                  # -> WRF-4.3.3/

# 2. WRF-WVTs modules (from the WRF-WVTs developers)
git clone https://github.com/damianinsua/WRF-WVTs.git
tar xf WRF-WVTs/modules_tracers_4.3.3.tar -C WRF-4.3.3

# 3. multi-tag patch (this repository)
git clone https://github.com/hadizkia/WRF-WVT-multitag.git
WRF-WVT-multitag/install.sh WRF-4.3.3          # up to 10 tags
#   WRF-WVT-multitag/install.sh WRF-4.3.3 20   # up to 20 tags

# 4. build as usual
cd WRF-4.3.3
./configure                 # dmpar (MPI) build, see "Limits"
./compile em_real >& compile.log
```

`install.sh` checks that the WRF-WVTs modules are present, applies
`patch/wrf-wvt-multitag.patch`, and (for a maximum other than 10) regenerates
the per-tag Registry entries with `tools/wvt_multitag/gen_wvt_multitag.py`.

Use the `real.exe` of the same build: it writes the extra tracer species to
`wrfinput`/`wrfbdy`, so set the same `tracer_opt` in real's `namelist.input`.

## Run

### 1. Masks

Make one `trmask_d01` holding one mask per tag: `TRMASK` for tag 1,
`TRMASK_T2` for tag 2, and so on (1 = source, 0 = elsewhere). The WRF-WVTs
rules apply to every tag: a 2D mask must be 0 in the relaxation zone, and
`TRMASK3D_T<k>` / `TRMASK3D2_T<k>` work as 3D source / sink for tag k.

From single-tag WRF-WVTs mask files:

```bash
python3 tools/make_trmask_multitag.py --start 1980-04-01_00:00:00 -o trmask_d01 \
    trmask_npac.nc trmask_gulf.nc trmask_land.nc
# tag 1 = npac, tag 2 = gulf, tag 3 = land  ->  tracer_opt = 43
```

WRF reads the masks at the start of a cold-start run, so the file's `Times`
must equal `start_date` (`--start` sets it). Restarts keep the masks from the
restart file.

### 2. namelist.input

Same as WRF-WVTs, except `tracer_opt`:

```
 &time_control
 io_form_auxinput8   = 2,
 auxinput8_inname    = "trmask_d<domain>",

 &physics
 scalar_pblmix       = 0,
 tracer_pblmix       = 0,

 &dynamics
 tracer_adv_opt      = 4,
 tracer_opt          = 43,     ; 4 = 1 tag (WRF-WVTs);  40+N = N tags (42 ... 50)
 tracer2dsource      = 1,
 tracer3dsource      = 0,
 tracer3dsink        = 0,
```

### 3. Output

Tag 1 keeps the WRF-WVTs names; tag k ≥ 2 adds `_t<k>` (lower-case names) or
`_T<k>` (upper-case names):

| field | tag 1 | tag 2 | tag k |
|---|---|---|---|
| tracer vapor, cloud, rain, ice, snow, graupel | `qv_tr` … `qg_tr` | `qv_tr_t2` … `qg_tr_t2` | `qv_tr_t<k>` … |
| grid-scale rain / snow / graupel | `TR_RAINNC`, `TR_SNOWNC`, `TR_GRAUPELNC` | `TR_RAINNC_T2`, … | `TR_RAINNC_T<k>`, … |
| cumulus rain | `TR_RAINC` | `TR_RAINC_T2` | `TR_RAINC_T<k>` |
| surface source flux | `TRQFX` | `TRQFX_T2` | `TRQFX_T<k>` |
| moisture-flux diagnostic | `TR_THUM_U_PHY_DT`, `TR_THUM_V_PHY_DT` | `…_T2` | `…_T<k>` |
| masks | `TRMASK`, `TRMASK3D`, `TRMASK3D2` | `TRMASK_T2`, … | `TRMASK_T<k>`, … |

If you trim output with an `iofields` file, add the tag-k names you want.

## How it works

- **Tag 1** goes through exactly the WRF-WVTs code path, untouched.
- **Tags 2..N** are handled next to every WRF-WVTs hook through a small tag
  table (`share/module_wvt_tags.F`), which `dyn_em/module_wvt_set.F` points at
  the current grid's per-tag fields each time step. The hooks covered: the
  surface source flux (`TRQFX`), the 3D source/sink, PBL and cumulus tendencies
  (coupling, decoupling, adding to the tracer tendency), cumulus rain
  accumulation and the end of a convective event, the moisture-flux diagnostic,
  and the cold-start initialisation.
- **Tracer schemes.** The WRF-WVTs versions of WSM6, YSU and Kain–Fritsch update
  the model state and the tracer together. For tags 2..N each scheme is called
  on a fresh copy of the model state it updates, then the normal tag-1 call
  advances the real model state once. This keeps every tag exactly equal to
  its own single-tag run without touching the schemes.
- **Registry.** `tools/wvt_multitag/gen_wvt_multitag.py N` generates
  `Registry/registry.wvt_multitag` (the tracer species and per-tag fields for
  tags 2..N, allocated only for the `tracer_opt` in use) and the pointer table.
  The default patch is generated for N = 10.

### Changing the maximum number of tags

```bash
cd WRF-4.3.3
python3 tools/wvt_multitag/gen_wvt_multitag.py 20     # up to 20 tags (tracer_opt 42 ... 60)
./clean; ./compile em_real
```

(`tracer_opt = 40 + N` must stay below 100, so the generator allows N ≤ 59.)

## Cost

Each extra tag adds 6 advected species and one more pass of the three tracer
schemes. In the 2-tag test below (121 × 101 × 45 grid, 48 MPI tasks, 12 h) the
second tag cost **~35 %** of a single-tag run, versus 100 % for a second
separate run, and the grid memory WRF allocates grew by 11 %.

## Limits

- Physics: WSM6 + Kain–Fritsch + YSU (what WRF-WVTs supports).
- Build: **dmpar (MPI)**. Tags 2..N copy the scheme inputs per tile, which
  assumes one tile per MPI task; with OpenMP tiling (`numtiles > 1`) and more
  than one tag the model stops with a clear message.
- Tested with WRF 4.3.3 and the WRF-WVTs 4.3.3 modules, Intel compilers
  (`-fp-model precise`), single domain. Nests are handled the same way per
  domain but have not been tested.

## Validation

All tests: 12 h from 1980-04-01 00 UTC, ERA5 initial and boundary conditions,
u/v grid nudging, WSM6 + Kain–Fritsch + YSU + Noah. "Production" is the
unmodified WRF 4.3.3 + WRF-WVTs build. Scripts are in `tests/`.

**2 tags, 121 × 101 domain** (south-western North America, 20–45° N, 125–95° W).
LL = local land source, ~LL = everything else.

| check | result |
|---|---|
| multi-tag build with `tracer_opt = 4` vs production: 24 model fields + 13 tag fields | identical (0 difference) |
| 2 tags, LL + LL: model fields vs production | identical |
| 2 tags, LL + LL: tag 1 vs production, tag 2 vs tag 1 | identical |
| 2 tags, LL + ~LL: model fields vs production | identical |
| 2 tags, LL + ~LL: tag 1 vs production LL run | identical |
| 2 tags, LL + ~LL: tag 2 vs production ~LL run | identical |

**3 tags, 941 × 421 domain** (30° S–75° N): tag 1 = North Pacific, tag 2 =
Gulf of Mexico / Atlantic, tag 3 = local land, each against its own
single-tag production WRF-WVTs run.

*Test running; results will be added here.*

## Repository

```
install.sh                         apply the patch to WRF 4.3.3 + WRF-WVTs
patch/wrf-wvt-multitag.patch       all source changes (against WRF 4.3.3 + WRF-WVTs 4.3.3 modules)
tools/gen_wvt_multitag.py          the Registry/pointer-table generator (also installed by the patch)
tools/make_trmask_multitag.py      combine single-tag masks into one multi-tag trmask_d01
tests/                             the validation runs above (SLURM scripts written for our cluster; adapt paths)
```

Files the patch adds to WRF: `share/module_wvt_tags.F`, `dyn_em/module_wvt_set.F`,
`Registry/registry.wvt_multitag`, `dyn_em/wvt_tags_set.h`, `share/wvt_max_tags.h`,
`tools/wvt_multitag/gen_wvt_multitag.py`. Files it changes: the WRF-WVTs hooks
in `dyn_em/` (solve_em, start_em, module_em, module_big_step_utilities_em),
`phys/` (microphysics, cumulus, PBL and surface drivers, module_physics_addtendc,
module_physics_init), `share/mediation_wrfmain.F`, `Registry/Registry.EM` and
the `share`/`dyn_em` Makefiles. Every change is marked `multi-tag WVT`.

## License

The multi-tag additions are released under the [MIT License](LICENSE).
WRF and WRF-WVTs keep their own terms; see the scope note in `LICENSE`.

## Build note

If `./compile` fails at the final link with `time: No such file or directory`,
your compute node lacks `/usr/bin/time`, which WRF's link line calls. Put a
stand-in first on `PATH` (`printf '#!/bin/bash\nexec "$@"\n' > ~/bin/time; chmod +x ~/bin/time`)
and run `./compile em_real` again.
