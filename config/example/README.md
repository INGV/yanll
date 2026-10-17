# Example configuration

The smallest configuration that proves the contract of `docs/configuration.md`: a
fictional network of six stations around 45.0 N 10.0 E (`stations.txt`), one
flat-layered 1D model called `synthetic` (`models/synthetic/`: the velocity model, the
Vel2Grid, Grid2Time and NLLoc templates, zero station corrections) and one event whose
arrival times were computed by Time2EQ on the very grids yanll builds, so that
`yanll-locate` must give its hypocenter back.

The event (`event/`): hypocenter at latitude 45.05, longitude 10.08, depth 8.0 km,
origin time 2026-01-01T00:00:00Z, exact P and S picks of class 0 at the six stations.
`event/time2eq.in` is the Time2EQ control that defines it; `event/event.json` is the
`yanll-locate` input made from Time2EQ's output by `scripts/make-example-event.sh`.
Neither file is read by yanll: they sit here because they belong to the example.

```
YANLL_CONFIG=./config/example docker compose run --rm -T yanll yanll-locate /config/event/event.json > out.json
YANLL_CONFIG=./config/example docker compose run --rm yanll /scripts/check-example.sh
YANLL_CONFIG=./config/example docker compose run --rm yanll /scripts/make-example-event.sh > config/example/event/event.json
```

The first run builds the model grid and twelve travel-time grids in seconds under
`${YANLL_DATA}/model/synthetic/` and `time/synthetic/`. The check locates the event and
compares with the hypocenter above within the project tolerance (1 km in epicentre,
2 km in depth, 0.5 s in origin time); the location comes back within a few tens of
metres and a millisecond. The same check is the `check-example` job of the CI.

To start a site from here: copy the directory, replace `stations.txt` with the site's
catalog (FDSN station text), `velocity.in` with the site's model, then set the grid
extents and spacing in `vel2grid.in` and `locate.in` and the search parameters in
`locate.in`; `TRANS` must be the same in the three templates.
