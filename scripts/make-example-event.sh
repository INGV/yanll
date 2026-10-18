#!/usr/bin/env bash
# Synthesize the observations of the example event and print the yanll-locate input
# document that config/example/event/event.json holds. Runs in the container with the
# example configuration mounted:
#
#   YANLL_CONFIG=./config/example docker compose run --rm yanll /scripts/make-example-event.sh > config/example/event/event.json
#
# The grids of every station of the catalog are built first (yanll-make-grids), then
# Time2EQ computes exact arrival times from the hypocenter of event/time2eq.in on those
# grids. Time2EQ dates every arrival 1900-01-01, writes the pick class as a float
# (QUAL 0.00e+00) and adds a PUBLIC_ID line: the arrivals get the event's origin date,
# 2026-01-01T00:00:00Z, and an integer class, and only arrival lines are kept, before
# yanll-obs2json reads them.
set -euo pipefail

readonly CONFIG="${YANLL_CONFIG:-/config}"
readonly DATA="${YANLL_DATA:-/data}"
readonly MODEL="synthetic"
readonly ORIGIN_DATE="20260101"

TMP=$(mktemp -d)
trap 'rm -rf "${TMP}"' EXIT

# shellcheck disable=SC2046
yanll-make-grids "${MODEL}" $(awk -F'|' '!/^#/ {print $2}' "${CONFIG}/stations.txt") >&2

{
    cat "${CONFIG}/event/time2eq.in"
    echo "EQFILES ${DATA}/time/${MODEL}/time ${TMP}/synthetic.obs"
} > "${TMP}/time2eq.in"
Time2EQ "${TMP}/time2eq.in" > "${TMP}/time2eq.log" 2>&1 \
    || { cat "${TMP}/time2eq.log" >&2; exit 1; }

awk -v DATE="${ORIGIN_DATE}" '
    /^#/ || NF < 11 { next }
    { $7 = DATE; $11 = int($11 + 0); print }' "${TMP}/synthetic.obs" > "${TMP}/event.obs"
yanll-obs2json --model "${MODEL}" "${TMP}/event.obs"
