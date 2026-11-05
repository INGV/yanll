# INGV configuration

The configuration yanll runs with at INGV, in the layout `docs/configuration.md`
describes. Generated: do not edit `models/` by hand.

- `models/` is written by `scripts/generate-ingv-config.py` from the production files
  under `reference/production/`: the 17 regional 1D models (one per zone of
  `centri_20211027.lst`, with the velocity model, the Vel2Grid and Grid2Time templates,
  the NLLoc template and the station corrections; `Sardegna_12` has no corrections) and
  the 3D model `TOMORAMA-2013` (Grid2Time and NLLoc templates, corrections, `cascade`
  with the production decimation `20,40,100`). Rerun the script after a change under
  `reference/` and commit.
- `stations.txt` is the station catalog, a snapshot of the INGV `fdsnws-station` service
  written by `scripts/fetch-stations.sh`; its first line says when and from where.
- The 3D model body is not here: copy `TOMORAMA_zmax800_deep.{P,S}.mod.{hdr,buf}` from
  the production host to `${YANLL_DATA}/model/TOMORAMA-2013/model.{P,S}.mod.{hdr,buf}`.

```
docker compose run --rm yanll yanll-locate /fixtures/events/47442632_147825511/input-1d.json
```
