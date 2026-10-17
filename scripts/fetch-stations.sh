#!/usr/bin/env bash
# Refresh the station snapshot used to generate the travel-time grids. Production asks
# the same legacy endpoint one station at a time (03_test_stations_3d.sh); the snapshot
# fetches every station once so that grid generation needs no network. The first line
# records when and from where it was taken.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
readonly URL="http://webservices.ingv.it/deprecated/fdsnws/station/1/query?level=station&format=text&authoritative=any&visibility=any"
readonly OUT="config/ingv/stations.txt"
readonly TMP="${OUT}.tmp"

{
    echo "# fetched $(date -u +%Y-%m-%dT%H:%M:%SZ) from ${URL}"
    curl -sSf --max-time 120 "${URL}"
} > "${TMP}"
LINES=$(grep -vc '^#' "${TMP}")
mv "${TMP}" "${OUT}"
echo "${OUT}: ${LINES} station lines"
