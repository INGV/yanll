# yanll: see README.md. `make check` runs every verification the repository has so far.

.PHONY: check check-reference

check: check-reference

check-reference:
	scripts/check-reference.sh
