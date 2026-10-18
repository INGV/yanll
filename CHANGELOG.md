# Release Notes

### Release 2.2.0 (2026-10-18)
  - ci: put the reference check in the resource group too, its checkout alone wiped a running test

### Release 2.1.0 (2026-10-18)
  - ci: run the docker jobs one at a time, the shared runner reuses one checkout for parallel jobs
  - ci: drop the manual comparison job, no runner has the data; it runs by hand on nll-dev (README)

### Release 2.0.0 (2026-10-18)
  - feat: move the INGV configuration out of the engine into config/ingv (YANLL_CONFIG templates)
  - feat: generate config/ingv from reference/ (scripts/generate-ingv-config.py), stations.txt there
  - feat: drop `dimension` from the JSON input, the model says what it is (fixture inputs redone)
  - feat: duplicate station codes take the first catalog line; grids in YANLL_DATA/{model,time}/
  - feat: add a synthetic example configuration located end to end (config/example, Time2EQ)
  - fix: exit 2 on every configuration error of yanll-locate, pointing at docs/configuration.md
  - build: image holds NLL and bin/ only; tests and yanll-compare run from mounts; linux/amd64 only
  - ci: locate the example configuration on every push
  - ci: publish to Docker Hub as ingv/yanll (develop -> :develop, vX.Y.Z -> :X.Y.Z and :latest)
  - docs: configuration contract (docs/configuration.md), README and json-schema for 2.0.0
  - docs: rerun the comparison with production on the 2.0.0 engine, 40 of 40, rows unchanged
  - docs: add the NLLoc input check to the comparison web page
  - ci: run the reference check and the JSON I/O tests on every push, the comparison on demand

### Release 1.0.0 (2026-10-16)
  - docs: describe the production NLL flow on nll.int.ingv.it with its scripts and 21 fixtures
  - feat: build NonLinLoc 7.1.05 (7a62fa46) in a Docker image with the 17 1D models and corrections
  - feat: generate the 1D and TOMORAMA-2013 3D station travel-time grids from the station snapshot
  - feat: locate from a JSON document and map the NLLoc output to JSON (yanll-locate, yanll-obs2json)
  - feat: compare container locations with production (yanll-compare): 40 of 40 within tolerance
  - fix: skip stations outside the 3D model instead of aborting the grids
  - docs: JSON schemas, comparison report with all-stations 3D rows, location table and web page
  - test: JSON I/O tests against the production fixtures, run inside the image
  - chore: drop the Makefile in favour of direct docker commands
