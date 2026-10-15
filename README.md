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
   locations against production. In progress.
3. A command-line tool that reads one JSON document (observations, model, 1D or 3D,
   station corrections, ...) and writes one JSON document with the location. Planned.

## Layout

| Path | Content |
|---|---|
| `docs/production-flow.md` | how a location is computed on the production host, inputs, control files, outputs, how to reproduce one by hand |
| `reference/production/` | read-only copies of the production scripts, models, corrections, control files and NLL 7.00.00 sources, paths mirrored, secrets removed (`reference/production/README.md`) |
| `fixtures/events/` | 21 recent production runs (observations, 1D and 3D `.hyp`) used as oracles for the comparison (`fixtures/events/README.md`) |
| `scripts/` | verification scripts |
| `Makefile` | `make check` runs every verification available so far |

## Checking

```
make check
```

Phase 1 is checked by `scripts/check-reference.sh`: every script and file named in
`docs/production-flow.md` must exist under `reference/production/` or `fixtures/`, and
no copied file may hold a credential.
