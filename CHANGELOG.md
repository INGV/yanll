# Release Notes

### Release 1.0.0-dev (2026-10-16)
  - docs: describe the production NLL flow on nll.int.ingv.it with its scripts and 21 fixtures
  - feat: build NonLinLoc 7.1.05 (7a62fa46) in a Docker image with the 17 1D models and corrections
  - feat: generate the 1D and TOMORAMA-2013 3D station travel-time grids from the station snapshot
  - feat: locate from a JSON document and map the NLLoc output to JSON (yanll-locate, yanll-obs2json)
  - feat: compare container locations with production (yanll-compare): 40 of 40 within tolerance
  - fix: skip stations outside the 3D model instead of aborting the grids
  - docs: JSON schemas, comparison report with all-stations 3D rows, location table and web page
  - test: JSON I/O tests against the production fixtures, run inside the image
  - chore: drop the Makefile in favour of direct docker commands
