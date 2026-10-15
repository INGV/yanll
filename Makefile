# yanll: see README.md. `make check` runs every verification the repository has.

.PHONY: check check-reference check-json compare

check: check-reference check-json

# Phase 1: every script and file docs/production-flow.md relies on is in the repo.
check-reference:
	scripts/check-reference.sh

# Phase 3: JSON I/O against the production fixtures, inside the image (needs the
# image built, the data directory and, the first time, about 3 minutes of grids).
check-json:
	docker compose run --rm yanll python3 -m unittest discover -s /opt/yanll/tests -v

# Phase 2: locate every fixture event in the container and compare with production
# (hours of grid generation the first time; writes docs/comparison-report.md).
compare:
	docker compose run --rm yanll yanll-compare
