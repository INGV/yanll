#!/usr/bin/env bash
# Locate the example event and check that the hypocenter Time2EQ was given comes back
# within the project tolerance (1 km in epicentre, 2 km in depth, 0.5 s in origin
# time). Runs in the container with the example configuration mounted, as the CI does:
#
#   YANLL_CONFIG=./config/example docker compose run --rm yanll /scripts/check-example.sh
#
# The expected hypocenter is read from the EQSRCE line of event/time2eq.in; the origin
# time is the convention of make-example-event.sh.
set -euo pipefail

readonly CONFIG="${YANLL_CONFIG:-/config}"
readonly ORIGIN_TIME="2026-01-01T00:00:00Z"

OUT=$(mktemp)
trap 'rm -f "${OUT}"' EXIT

yanll-locate -o "${OUT}" "${CONFIG}/event/event.json"
python3 - "${OUT}" "${CONFIG}/event/time2eq.in" "${ORIGIN_TIME}" <<'EOF'
import datetime as dt
import json
import math
import sys

out, control, origin_time = sys.argv[1:]
result = json.load(open(out))
lat, lon, dep = [float(v) for line in open(control) if line.startswith("EQSRCE") for v in line.split()[3:6]]
ot = dt.datetime.fromisoformat(origin_time.replace("Z", "+00:00"))
got = result["origin"]
got_ot = dt.datetime.fromisoformat(got["time"].replace("Z", "+00:00"))

d_lat = (got["latitude"] - lat) * 111.2
d_lon = (got["longitude"] - lon) * 111.2 * math.cos(math.radians(lat))
d_epi = math.hypot(d_lat, d_lon)
d_dep = got["depth"] - dep
d_ot = (got_ot - ot).total_seconds()
ok = d_epi <= 1.0 and abs(d_dep) <= 2.0 and abs(d_ot) <= 0.5
print(f"expected {lat} {lon} {dep} km {origin_time}")
print(f"located  {got['latitude']:.4f} {got['longitude']:.4f} {got['depth']:.2f} km {got['time']}")
print(f"d_epi={d_epi:.3f} km d_dep={d_dep:+.3f} km d_ot={d_ot:+.3f} s phases={result['quality']['phases_used']} {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
EOF
