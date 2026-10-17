#!/usr/bin/env python3
"""Generate the INGV configuration of yanll, config/ingv/models/, from reference/production.

The engine knows nothing about INGV: every production fact lives here and is written
literally into the NLL control-file templates the engine fills at run time (see
docs/configuration.md for the contract). This script is the production chain read
once and written down:

- the zone table centri_20211027.lst gives, per 1D zone, the TRANS origin and the half
  extents of the location grid; 04_locator_nll_1d.sh turns the extents into LOCGRID
  with awk arithmetic that is reproduced here digit for digit, as the fixture control
  files are compared byte for byte;
- Auto_Create_Model_Grid_NewZones.sh gives the Vel2Grid and Grid2Time control files of
  a zone, which take the first LAYER depth of the model as grid top;
- 04_locator_nll_3d.sh builds the 3D LOCGRID from the TOMORAMA-2013 model header with
  the grid top forced to -4 km; run_casc_grid.sh decimates the 3D time grids at 20, 40
  and 100 km;
- the station corrections are the per-zone correzioni_<zone>.in (none for Sardegna_12)
  and corrections_TOMORAMA-2013.in.

The 3D model body (TOMORAMA_zmax800_deep.{P,S}.mod.{hdr,buf}, 1.2 GB) is not in the
repository: it goes to ${YANLL_DATA}/model/TOMORAMA-2013/ by hand, as config/ingv/README.md
says. The station catalog config/ingv/stations.txt is refreshed by scripts/fetch-stations.sh,
not written here.

Run from the repository root; the models/ directory is rebuilt from scratch so that a
zone removed from the table disappears. Commit the result.
"""
import os
import shutil
import sys

REF = "reference/production/opt/nll"
ZONES_DIR = f"{REF}/run/modelli_20211027"
ZONE_TABLE = f"{ZONES_DIR}/centri_20211027.lst"
CORRECTIONS_3D = f"{REF}/run/corrections_3d/corrections_TOMORAMA-2013.in"
MODEL_3D_HDR = f"{REF}/model_TOMORAMA-2013/TOMORAMA_zmax800_deep.P.mod.hdr"
OUT = "config/ingv/models"

# The production heredocs pad this line with 48 blanks; the byte comparison keeps them.
CONTROL_LINE = "CONTROL 2 123456" + " " * 48

LOCSIG = "LOCSIG INGV - Istituto Nazionale di Geofisica e Vulcanologia"
LOCFILES = "LOCFILES @OBS@ NLLOC_OBS @TIME@  @OUT@"
COMMON_TAIL = [
    "LOCPHASEID  P   P p G PN Pn PG Pg",
    "LOCPHASEID  S   S s G SN Sn SG Sg",
    "LOCQUAL2ERR 0.05 0.2 0.45 0.8 99999.9",
    "@CORRECTIONS@",
]

# Vel2Grid invocation of Auto_Create_Model_Grid_NewZones.sh: 2D grid, 600 km across and
# 114 km deep at 0.1 km, top at the first model layer.
MODEL_NX, MODEL_NZ, MODEL_STEP = 6001, 1141, 0.1


def zones():
    """(nickname, raw lat0, raw lon0, half_x, half_y) per row of the zone table.

    The raw strings matter: Auto_Create_Model_Grid_NewZones.sh writes them as read into
    the Vel2Grid TRANS line (43.5000), 04_locator_nll_1d.sh reformats them with %.6f."""
    out = []
    with open(ZONE_TABLE) as fin:
        next(fin)
        for line in fin:
            f = line.split()
            if len(f) > 11:
                out.append((f"{f[4]}_{f[2]}", f[11], f[10], float(f[8]), float(f[9])))
    return out


def model_min_depth(zone):
    """The first LAYER depth of the zone model, as the raw string of the file."""
    with open(f"{ZONES_DIR}/model_{zone}.in") as fin:
        for line in fin:
            if not line.startswith("#"):
                return line.split()[1]


def awk_num(x):
    """A number the way awk prints it: no decimals when integral, else %.6g."""
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.6g}"


def locgrid_1d(half_x, half_y, min_depth):
    """The LOCGRID of 04_locator_nll_1d.sh: model step x5, extent from the zone table,
    two nodes dropped at the top and bottom, origin so that the grid is centred."""
    step = MODEL_STEP * 5.0
    nx = (half_x * 2) / step + 1
    ny = (half_y * 2) / step + 1
    nz = ((MODEL_NZ - 1) * MODEL_STEP) / step + 1 - 4
    x0 = (nx - 1) * step / -2
    y0 = (ny - 1) * step / -2
    z0 = float(min_depth) + step * 2
    z0 = 0 if z0 > 0 else z0
    return " ".join(awk_num(v) for v in (nx, ny, nz, x0, y0, z0, step, step, step))


def write(path, lines):
    with open(path, "w") as fout:
        fout.write("\n".join(lines) + "\n")


def write_zone(zone, lat0, lon0, half_x, half_y):
    d = f"{OUT}/{zone}"
    os.makedirs(d)
    min_depth = model_min_depth(zone)
    trans = f"TRANS SIMPLE {float(lat0):.6f} {float(lon0):.6f} 0.0"
    write(f"{d}/locate.in", [
        CONTROL_LINE,
        trans,
        LOCSIG,
        "LOCCOM INGV-1D (NonLinLoc Location)",
        LOCFILES,
        "LOCHYPOUT  SAVE_NLLOC_ALL",
        "LOCSEARCH  OCT 20 20 10 0.02 20000 5000 0 1",
        "#LOCSEARCH  OCT 20 20 10 0.02 20000 5000 0 1",
        f"LOCGRID  {locgrid_1d(half_x, half_y, min_depth)}  PROB_DENSITY  SAVE",
        "LOCMETH EDT_OT_WT 9999.0 3 -1 -1 -1 -1 -1. 1",
        "LOCGAU 0.2 0.0",
        "LOCGAU2 0.05 0.1 5.0",
    ] + COMMON_TAIL)
    write(f"{d}/vel2grid.in", [
        CONTROL_LINE,
        f"TRANS SIMPLE {lat0} {lon0} 0.0",
        "VGOUT  @MODEL@",
        "VGTYPE @PHASE@",
        f"VGGRID 2 {MODEL_NX} {MODEL_NZ} 0.0 0.0 {min_depth}  0.1 0.1 0.1 SLOW_LEN",
        "INCLUDE @CONFIG@/velocity.in",
        "GTMODE GRID2D ANGLES_NO",
    ])
    # ANGLES_NO where production has ANGLES_YES: it writes angle grids and never reads
    # them (no LOCANGLES in any control file).
    write(f"{d}/grid2time.in", [
        CONTROL_LINE,
        trans,
        "VGTYPE @PHASE@",
        f"VGGRID 2 {MODEL_NX} {MODEL_NZ} 0.000000 0.000000 {float(min_depth):.6f} 0.100000 0.100000 0.100000 SLOW_LEN",
        "GTFILES @MODEL@ @TIME@ @PHASE@",
        "GTMODE GRID2D ANGLES_NO",
        "@STATIONS@",
        "GT_PLFD  1.0e-3  0",
    ])
    shutil.copyfile(f"{ZONES_DIR}/model_{zone}.in", f"{d}/velocity.in")
    corrections = f"{ZONES_DIR}/correzioni/correzioni_{zone}.in"
    if os.path.exists(corrections):
        shutil.copyfile(corrections, f"{d}/corrections.in")


def write_3d():
    d = f"{OUT}/TOMORAMA-2013"
    os.makedirs(d)
    # The location grid is the whole model grid as its header states it, with the top
    # forced to -4 km (04_locator_nll_3d.sh).
    with open(MODEL_3D_HDR) as fin:
        f = fin.readline().split()
    grid = " ".join(f[0:5] + ["-4"] + f[6:9])
    write(f"{d}/locate.in", [
        CONTROL_LINE,
        "TRANS  TRANS_MERC WGS-84  0.0 15.0  0.0",
        LOCSIG,
        "LOCCOM INGV-3d (NonLinLoc Location)",
        LOCFILES,
        "LOCHYPOUT  SAVE_NLLOC_ALL",
        "#LOCHYPOUT SAVE_NLLOC_ALL NLL_FORMAT_VER_2 # Valutare l'uso del formato 2",
        "LOCSEARCH OCT 24 24 20 0.01 50000 5000 0 1",
        f"LOCGRID  {grid}  PROB_DENSITY  SAVE",
        "LOCMETH EDT_OT_WT 9999.0 3 150 0 -1.80 300 -1 1",
        "LOCGAU 0.2 0.0",
        "LOCGAU2 0.01 0.05 2.0 # 3D",
    ] + COMMON_TAIL)
    # run_casc_grid.sh: one Grid2Time per station on the full grid, then the cascading
    # decimation NLLoc reads.
    write(f"{d}/grid2time.in", [
        "CONTROL 1 54321",
        "TRANS TRANS_MERC WGS-84  0.0 15.0  0.0",
        "GTMODE GRID3D ANGLES_NO",
        "GT_PLFD  1.0e-3  0",
        "@STATIONS@",
        "GTFILES  @MODEL@  @TIME@   @PHASE@",
    ])
    write(f"{d}/cascade", ["20,40,100"])
    shutil.copyfile(CORRECTIONS_3D, f"{d}/corrections.in")


def main():
    if not os.path.isdir(ZONES_DIR):
        sys.exit("run from the repository root")
    shutil.rmtree(OUT, ignore_errors=True)
    for zone in zones():
        write_zone(*zone)
    write_3d()
    print(f"{OUT}: {len(os.listdir(OUT))} models")


if __name__ == "__main__":
    main()
