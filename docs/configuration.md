# Configuration

yanll is a general NonLinLoc (NLL) engine: it owns the JSON input and output and the
life cycle of the grids, nothing else. Everything NLL needs to know about a site, which
velocity models exist, how they are projected and gridded, how a location is searched,
which stations exist and what their corrections are, is the site's and lives in one
directory, mounted read-only in the container at the path `YANLL_CONFIG` names
(`/config` in the image). The mechanism is NLL's own: the directory holds NLL
control-file templates with a few placeholders yanll fills at run time. There is no
parameter schema of yanll's own, no keyword is written by yanll except through a
placeholder, and the site's templates can use any keyword NLL accepts.

Two configurations are in the repository: `config/example/`, a small synthetic 1D case
that proves the contract end to end (see `config/example/README.md`), and `config/ingv/`,
the INGV configuration generated from the production host (see below).

## Layout

```
${YANLL_CONFIG}/
  stations.txt                 station catalog, FDSN station text
  models/<name>/               one directory per model; <name> is what the JSON input names
    locate.in                  NLLoc control file template               required
    grid2time.in               Grid2Time control file template           required
    vel2grid.in                Vel2Grid control file template            optional, see below
    velocity.in                the velocity model vel2grid.in INCLUDEs   by convention
    corrections.in             LOCDELAY lines                            optional
    cascade                    GridCascadingDecimate steps, e.g. 20,40,100   optional
```

yanll reads only these files; anything else in the directory is ignored, so a README
or the control file of a test event can sit next to them.

A model name is a directory name: letters, digits, `_`, `-` and `.`, starting with a
letter or digit. The JSON input selects the model by this name and nothing else: yanll
has no notion of 1D or 3D, of zones or of regions. A model is "1D" only in the sense
that it has a `vel2grid.in` and yanll can build its grid; a model whose grid is built
elsewhere (a 3D tomography) simply has none.

## Placeholders

A placeholder is `@NAME@`, replaced by plain text substitution: nothing else in the
template is interpreted, so a `$` or a `{` in a comment is safe, and a template can be
written from a shell heredoc without quoting. A `@NAME@` that yanll does not know is an
error that names the template, before NLL runs. yanll does not check that a template
uses a placeholder: a `locate.in` without `@CORRECTIONS@` never includes corrections,
whatever the input says.

| Placeholder | Template | Replaced by |
|---|---|---|
| `@OBS@` | `locate.in` | path of the `NLLOC_OBS` observation file yanll writes from the input |
| `@TIME@` | `locate.in` | travel-time grid root of the model, `${YANLL_DATA}/time/<name>/time` |
| `@TIME@` | `grid2time.in` | the root Grid2Time writes to: a staging directory under `time/<name>/tmp/`, from which yanll moves (or decimates, see `cascade`) the finished grid into `time/<name>/` |
| `@OUT@` | `locate.in` | output root of the run; yanll reads `<root>.grid0.loc.hyp` |
| `@CORRECTIONS@` | `locate.in` | a whole line: `INCLUDE ${YANLL_CONFIG}/models/<name>/corrections.in` when the input has `station_corrections: true`, the same line commented out (`#INCLUDE ...`) when false |
| `@MODEL@` | `vel2grid.in`, `grid2time.in` | model grid root, `${YANLL_DATA}/model/<name>/model` (for `VGOUT` and `GTFILES`) |
| `@PHASE@` | `vel2grid.in`, `grid2time.in` | `P` or `S`: both templates are rendered once per phase |
| `@STATIONS@` | `grid2time.in` | one `GTSRCE` line, see the catalog below; the template is rendered once per station and phase |
| `@CONFIG@` | `vel2grid.in`, `grid2time.in` | the model's own directory, `${YANLL_CONFIG}/models/<name>`, for `INCLUDE @CONFIG@/velocity.in` |

## What the templates must contain

The templates are complete NLL control files once the placeholders are filled; the NLL
documentation of each program is the reference. What yanll relies on:

- `locate.in`: `LOCFILES @OBS@ NLLOC_OBS @TIME@ @OUT@` and `LOCHYPOUT SAVE_NLLOC_ALL`,
  since yanll writes the observation file in `NLLOC_OBS` format and reads the
  `.grid0.loc.hyp`; `LOCQUAL2ERR`, since the `quality` of each observation is written as
  the `QUAL` class NLLoc maps through it; `LOCPHASEID` for every phase label the input
  may carry. `LOCSIG`, `LOCCOM`, `LOCGRID`, `LOCSEARCH`, `LOCMETH`, `LOCGAU`, `LOCGAU2`
  and anything else are the site's choices; yanll echoes the whole rendered file in the
  output document (`nll.control_file`).
- `grid2time.in`: `GTFILES @MODEL@ @TIME@ @PHASE@`, `@STATIONS@`, and a `GTMODE`
  (`GRID2D` for a 1D model, `GRID3D` otherwise; `ANGLES_NO` unless the site reads angle
  grids). The time grids NLLoc reads are `time.<phase>.<STA>.time.{hdr,buf}` under
  `time/<name>/`, as `GTFILES` names them.
- `vel2grid.in`, when present: `VGOUT @MODEL@`, `VGTYPE @PHASE@`, `VGGRID`, and the model
  itself, typically `INCLUDE @CONFIG@/velocity.in` with `LAYER` lines. The grid is
  written as `model.{P,S}.mod.{hdr,buf}` under `model/<name>/`.
- `CONTROL` and `TRANS` in the three templates must agree with each other and with the
  model grid: NLLoc, Grid2Time and the grid header must share the projection.
- `corrections.in`: `LOCDELAY` lines, included as they are. The input may ask for
  `station_corrections: true` only when the file exists; otherwise the run is refused.
- `cascade`: one line with the decimation steps passed to `GridCascadingDecimate` (for
  example `20,40,100`: full resolution to 20 km from the station, then coarser). When
  present, every time grid is decimated after Grid2Time and the decimated grid takes
  the final name; this is how a 3D model of hundreds of millions of nodes stays
  readable. Without the file the Grid2Time output is used as it is.

## The station catalog

`stations.txt` is FDSN station text as the `fdsnws-station` web service writes it with
`format=text&level=station`: lines starting with `#` are comments, fields are separated
by `|` in the order `Network|Station|Latitude|Longitude|Elevation|SiteName|StartTime|EndTime`.
yanll uses the station code (field 2) as the only key, as the observation file does:
network, location and channel play no part. Latitude and longitude are decimal degrees,
elevation metres. The `GTSRCE` line written for a station is

```
GTSRCE <code>  LATLON <lat> <lon> 0.0 <elevation km>
```

One rule for every model: a code listed more than once (the same station under two
networks) takes its first line, and the extra lines are reported on stderr; a code
absent from the catalog is reported and skipped, and NLLoc gives its phases weight 0
(the output marks them `"used": false` with no station coordinates). Refresh the
catalog by replacing the file; the INGV one is written by `scripts/fetch-stations.sh`.

## The data directory

Grids are large and derived, so they live outside the configuration, in the directory
`YANLL_DATA` names (`/data` in the image), written by yanll on demand:

```
${YANLL_DATA}/
  model/<name>/model.{P,S}.mod.{hdr,buf}      model grid: Vel2Grid output, or put there by the site
  model/<name>/vel2grid.{P,S}.in              the rendered Vel2Grid control files
  time/<name>/time.{P,S}.<STA>.time.{hdr,buf} travel-time grids, one pair per station and phase
  time/<name>/tmp/                            runs in progress (rendered control files, logs, Grid2Time output before it moves) and Grid2Time's copy of the model grid, time.{P,S}.mod.*
  locate/<run>/                               work directory of a location, removed on success unless --keep
  compare/                                    work directories of tests/yanll-compare
```

A model without `vel2grid.in` needs its grid placed by hand before the first location,
under `model/<name>/` with exactly these names (`model.P.mod.hdr`, `model.P.mod.buf`,
`model.S.mod.hdr`, `model.S.mod.buf`); until then every tool stops with a message
naming the directory. Nothing in the data directory is specific to a configuration
beyond the model names: two sites with a model of the same name must not share it.

### Adding and changing things

- A new model: create `models/<name>/` with its templates; the next input naming it
  builds what it needs.
- A new station: add its line to `stations.txt`; its grids are built the first time an
  input uses it.
- A station moved or changed elevation: edit the catalog and delete its grids in every
  model, `rm ${YANLL_DATA}/time/*/time.[PS].<STA>.time.*`; they are rebuilt on demand.
  A grid is never rebuilt while both its `.buf` exist, whatever the catalog says now.
- A velocity model changed: delete `model/<name>/` and `time/<name>/`, since every
  travel-time grid depends on the model grid.
- Station corrections changed: nothing to delete, `corrections.in` is read at every run.
- A model removed: delete its directory in the configuration and, at leisure, its
  `model/<name>/` and `time/<name>/`.

## What happens when the configuration is missing

Every tool (`yanll-locate`, `yanll-make-grids`) checks what it needs before running
NLL and exits with code 2 and a message on stderr that names the missing file and this
document: no directory at `YANLL_CONFIG`, no `models/`, a model directory without
`locate.in` or `grid2time.in`, no `stations.txt`, a model grid absent with no
`vel2grid.in` to build it, a placeholder yanll does not know. A model name with no
directory at all is an input error (`unknown model`, also exit 2, listing the models the
configuration has). What `yanll-make-grids` finds is repeated on `yanll-locate`'s stderr
when it runs it. `yanll-obs2json` reads no configuration: it only converts an
observation file to an input document.

## The INGV configuration

`config/ingv/` is written by `scripts/generate-ingv-config.py` from the production
scripts and files copied under `reference/production/` (how production builds its
control files is `docs/production-flow.md`): 17 regional 1D models, named by zone
(`Alpi-Occidentali_1`, ..., `Sardegna_12`), each with `vel2grid.in`, `velocity.in`,
`grid2time.in`, `locate.in` and, except `Sardegna_12`, `corrections.in`; and the 3D model
`TOMORAMA-2013` with `grid2time.in`, `locate.in`, `corrections.in` and `cascade`. The
generator writes every production fact literally into the templates: the zone's
`TRANS` origin, the `LOCGRID` arithmetic of the production script, the signature and
comment lines. Rerun it after a change under `reference/` and commit the result; the
station catalog `config/ingv/stations.txt` is refreshed by `scripts/fetch-stations.sh`
instead. The 3D model body is not in the repository (1.2 GB): copy the production pair
`TOMORAMA_zmax800_deep.{P,S}.mod.{hdr,buf}` to `${YANLL_DATA}/model/TOMORAMA-2013/` as
`model.{P,S}.mod.{hdr,buf}` (checksums in `docs/production-flow.md`, section 2.2).

The tests in `tests/` and the comparison `tests/yanll-compare` run with this
configuration mounted and prove that the rendered control files are production's byte
for byte and that the locations reproduce production (`README.md`, Checking).
