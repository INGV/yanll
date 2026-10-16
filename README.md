# yanll

yanll restructures NonLinLoc (NLL) into a containerized JSON-in / JSON-out locator for
the INGV seismic monitoring room, so that a location can be computed reproducibly on any
Docker host and, later, served to other software (Caravel/Apollo). It builds NLL from
the upstream repository and regenerates the regional travel-time grids from the
production model inputs; it does not replicate the production automation on
`nll.int.ingv.it` (event polling, MySQL, web page), which is only where NLL's
configuration is learned and the comparison cases come from.

Work proceeds in three phases, each usable on its own:

1. `docs/production-flow.md`: how NLL is used in production, with every script and
   configuration file it relies on copied under `reference/production/`. Done.
2. Docker images with NLL built from source at a pinned commit and the scripts that
   generate the station travel-time grids (Vel2Grid, Grid2Time) for the 17 regional 1D
   models and the TOMORAMA-2013 3D model, plus a scripted comparison of the container's
   locations against production. Done: `docs/comparison-report.md`, every fixture
   event within tolerance in 1D and 3D.
3. A command-line tool, `yanll-locate`, that reads one JSON document (observations,
   model, 1D or 3D, station corrections) and writes one JSON document with the
   location. Done: schemas in `docs/json-schema.md`, tests under `tests/`.

## Layout

| Path | Content |
|---|---|
| `docs/production-flow.md` | how a location is computed on the production host, inputs, control files, outputs, how to reproduce one by hand |
| `docs/comparison-report.md` | the container's locations against production for the fixture events, written by `yanll-compare` |
| `docs/comparison-table.md`, `docs/comparison-table.json` | the same comparison location by location, with the quality and uncertainty of each `.hyp`, as a table and as data |
| `docs/comparison-viz.html` | self-contained page for researchers: map of the events, input check, acceptance test and all-stations rows charted from the embedded data |
| `docs/json-schema.md` | input and output documents of `yanll-locate` |
| `reference/production/` | read-only copies of the production scripts, models, corrections, control files and NLL 7.00.00 sources, paths mirrored, secrets removed (`reference/production/README.md`) |
| `fixtures/events/` | 21 recent production runs (observations, 1D and 3D `.hyp`, and the same observations as `input-{1d,3d}.json`) used as oracles (`fixtures/events/README.md`) |
| `stations/fdsnws-station.txt` | snapshot of the INGV station list the grids are generated from (`scripts/fetch-stations.sh` refreshes it) |
| `Dockerfile`, `compose.yaml` | the image: NLL built from upstream at a pinned commit, the production model inputs, the scripts below |
| `bin/` | scripts shipped in the image: `yanll-locate` (JSON in, JSON out), `yanll-obs2json` (production observation file to input JSON), `yanll-make-grids` (model and travel-time grids), `yanll-compare` (comparison with production) |
| `tests/` | JSON I/O tests, run inside the image (see Checking) |
| `scripts/` | host-side scripts: verification, station snapshot refresh |

There is no Makefile on purpose: every build, run and check is a direct `docker`
command (or the shell script it names), as listed below.

## Building the image

```
docker compose build
```

The build clones https://github.com/ut-beg-texnet/NonLinLoc at the commit pinned in the
`Dockerfile` (`NLL_COMMIT`), compiles it with CMake on `debian:bookworm-slim` and copies
`NLLoc`, `Vel2Grid`, `Grid2Time` and `GridCascadingDecimate` into the runtime image
together with the 17 regional 1D models, the station corrections and the station
snapshot. The image is about 120 MB. Bump the commit on purpose, in its own commit, and
rerun the comparison: that is the only way to see what a bump changes.

## The data directory

Grids are large and derived, so they live outside the image in the directory that
`YANLL_DATA` names (`./data` by default, mounted at `/data` in the container). The
container writes there as root unless `YANLL_USER=uid:gid` is set (the directory must
then be writable by that user). On an NFS export with root squash, as `/mnt/nll` on
`nll-dev`, root in the container cannot write at all: set `YANLL_USER` to a user that
can.

```
model_1d/<zone>/model.{P,S}.mod.{hdr,buf}   1D model grids, written by Vel2Grid on first use (110 MB per zone)
model_3d/model.{P,S}.mod.{hdr,buf}          the TOMORAMA-2013 3D model, to be put there by hand
time_1d/<zone>/time.{P,S}.<STA>.time.*      1D travel-time grids, 55 MB each, about 1.5 s each to generate
time_3d/TOMORAMA-2013/time.{P,S}.<STA>.time.*   3D cascading grids, 22 MB each, about 2 min 15 s each (P and S run side by side)
compare/<run>/<dim>/                        work directories of yanll-compare
```

The 3D model is the pair `TOMORAMA_zmax800_deep.{P,S}.mod.{hdr,buf}` of the production
host (`/opt/nll/model_TOMORAMA-2013/`, 605 MB per `.buf`, checksums in
`docs/production-flow.md` section 2.2), copied as `model_3d/model.{P,S}.mod.{hdr,buf}`.
Without it only 1D locations work. On `nll-dev` the data directory is
`YANLL_DATA=/mnt/nll/yanll` with `YANLL_USER=1000:1000`, and the pair is in its
`model_3d/`.

## Generating grids

```
docker compose run --rm yanll yanll-make-grids <model> <station>...
```

`<model>` is a zone nickname (`Fascia-Appenninica_5b`, ..., see
`docs/production-flow.md` section 2.1) or `TOMORAMA-2013`. The script writes the model
grid of the zone if missing and a travel-time grid for every listed station that has
none yet, with the production control files (`ANGLES_NO`: production writes angle
grids and never reads them). Station coordinates come from the snapshot; a station
missing from it, or outside the 3D model (Lampedusa, stations abroad), is reported
and skipped, and its phases get weight 0 in the location, as in production. The full production set (17 zones, about 800 stations each, plus
1100 stations in 3D) would take about 1.5 TB and days of CPU: generate what the events
at hand need.

### When a station or a model changes

A grid is generated only when it is missing: a station is skipped as soon as both
`time.P.<STA>.time.buf` and `time.S.<STA>.time.buf` exist in the model's directory,
whatever the snapshot says now. Invalidating is by hand, by deleting files from the data
directory; the next run regenerates what is missing (an interrupted run leaves no partial
grid, the final `.buf` appears only at the end).

- Station coordinates or elevation changed: refresh the snapshot
  (`scripts/fetch-stations.sh`), rebuild the image (the snapshot is copied into it) and
  delete the station's grids in every model that has them:
  `rm ${YANLL_DATA}/time_1d/*/time.[PS].<STA>.time.{hdr,buf}` and
  `rm ${YANLL_DATA}/time_3d/TOMORAMA-2013/time.[PS].<STA>.time.{hdr,buf}`.
- 1D velocity model of a zone changed (`reference/production/opt/nll/run/modelli_20211027`
  is what the image ships): rebuild the image and delete `model_1d/<zone>/` and
  `time_1d/<zone>/`, since every travel-time grid depends on the model grid.
- 3D model changed: replace `model_3d/` and empty `time_3d/TOMORAMA-2013/`.
- Station corrections changed: nothing to delete, they are read from the control file at
  every run; rebuild the image.

## Comparing with production

```
docker compose run --rm yanll yanll-compare            # all fixture events, writes docs/comparison-report.md
docker compose run --rm yanll yanll-compare --dims 1d --report /data/compare/one.md 47442632_147825511
```

For every run under `fixtures/events/` the production control file is reused with its
paths rewritten, the grids are generated for the stations of the observation file (3D:
for the stations that had a grid in production, so that both locations see the same
phases), NLLoc runs, and the maximum-likelihood hypocentres are compared: 1 km in
epicentre, 2 km in depth, 0.5 s in origin time. `--all-stations` adds an informative 3D
row per event (`3d-all`) with grids for every station: production has had no 3D grid
for stations added since June 2023 (`docs/production-flow.md` section 6), so those rows
show what the missing grids cost. The report lists, per event and dimension,
both locations, the differences, the number of phases used and the largest offset
between the station coordinates of the two runs.

## Locating one event

```
docker compose run --rm -T yanll yanll-locate /fixtures/events/47442632_147825511/input-1d.json > out.json
docker compose run --rm -T yanll yanll-locate - < input.json > out.json
```

The input names the model (a zone or `TOMORAMA-2013`), the dimension, whether to
apply the station corrections, and the arrivals; the output carries the
maximum-likelihood hypocentre, the expectation, the quality and uncertainty blocks of
the `.hyp`, one entry per phase and the control file that was run. Both documents are
described in `docs/json-schema.md`. The tool generates the grids the stations need on
the fly (seconds in 1D, minutes per new station in 3D); the grids stay in the data
directory, the work directory under `locate/` is removed unless `--keep` is given or
the run fails. A production observation file becomes an input document with
`yanll-obs2json --model <model> --dimension <1d|3d> <file>`.

## Checking

```
scripts/check-reference.sh
docker compose run --rm yanll python3 -m unittest discover -s /opt/yanll/tests -v
```

The first command is the phase-1 check (every script and file named in
`docs/production-flow.md` exists under `reference/production/` or `fixtures/`, no copied
file holds a credential); the second runs the JSON I/O tests inside the image (phase 3: the
observation file and the control file written from the fixture inputs are the
production ones byte for byte, paths aside, for all 21 events in 1D and 3D; the
committed input documents are what `yanll-obs2json` writes; one 1D location reproduces
production within tolerance; malformed inputs are rejected). The tests need the image,
the data directory, and about 3 minutes of grid generation the first time. The
comparison of phase 2 is `docker compose run --rm yanll yanll-compare` (hours of grids
the first time) and its report is committed in `docs/comparison-report.md`.

GitLab CI (`.gitlab-ci.yml`) runs the first two commands on every push, building the
image first; the comparison is a manual job of the same pipeline that keeps the report as
an artifact.
