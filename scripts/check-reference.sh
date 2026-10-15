#!/usr/bin/env bash
# Phase-1 check: every production path and script that docs/production-flow.md relies
# on must be present in reference/production/, the fixtures it points to must exist, and
# no copied file may still hold a credential.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
readonly DOC="docs/production-flow.md"
readonly REF="reference/production"
FAILED=0

# 1. Scripts named in the document (anything ending in .sh or .py) must be in usr/bin
#    or elsewhere under the reference tree.
for NAME in $(grep -oE '`[A-Za-z0-9_./-]+\.(sh|py)`' "${DOC}" | tr -d '`' | xargs -n1 basename | sort -u); do
    if ! find "${REF}" -name "${NAME}" | grep -q .; then
        echo "MISSING script: ${NAME}"
        FAILED=1
    fi
done

# 2. Explicit repository paths quoted in the document must exist.
for P in $(grep -oE '`(reference/production|fixtures/events)/[A-Za-z0-9_./*{},-]+' "${DOC}" | tr -d '`' | sort -u); do
    case "${P}" in
        *\**|*\{*) continue ;;   # globs are illustrative
    esac
    if [[ ! -e "${P}" ]]; then
        echo "MISSING path: ${P}"
        FAILED=1
    fi
done

# 3. Production paths quoted as /opt/nll/... or /mnt/nll/... that name a file
#    (not a directory, not a generated or excluded artefact) must have a mirror copy.
for P in $(grep -oE '`/(opt|mnt)/nll/[A-Za-z0-9_./-]+\.(sh|py|in|lst|hdr|csh|f90|kml|txt)`' "${DOC}" | tr -d '`' | sort -u); do
    case "${P}" in
        *station_test*|*/tmp/*|*nll_temp_*|*TOMORAMA*.txt|*model_\<*) continue ;;
    esac
    if [[ ! -e "${REF}${P}" ]]; then
        echo "MISSING mirror: ${REF}${P}"
        FAILED=1
    fi
done

# 4. The 17 zone models, corrections and headers, and the fixture layout.
for ZONE in Alpi-Occidentali_1 Alpi-Centrali_2 Alpi-Orientali_3 Pianura-Padana_4 \
            Fascia-Appenninica_5a Fascia-Appenninica_5b Fascia-Appenninica_5c Fascia-Appenninica_5d \
            Fascia-Adriatica_6a Fascia-Adriatica_6b Gargano_7 Salento_8 \
            Fascia-Tirrenica_9a Fascia-Tirrenica_9b Calabria_10 Sicilia_11 Sardegna_12; do
    for F in "${REF}/opt/nll/run/modelli_20211027/model_${ZONE}.in" \
             "${REF}/opt/nll/models_20211027/model_${ZONE}/model.P.mod.hdr" \
             "${REF}/opt/nll/zones_20211128/${ZONE}.kml"; do
        [[ -e "${F}" ]] || { echo "MISSING zone file: ${F}"; FAILED=1; }
    done
done
for RUN in fixtures/events/*/; do
    for SUB in obs loc_1d loc_3d; do
        [[ -d "${RUN}${SUB}" ]] || { echo "MISSING fixture dir: ${RUN}${SUB}"; FAILED=1; }
    done
    ls "${RUN}"loc_1d/*.grid0.loc.hyp "${RUN}"loc_3d/*.grid0.loc.hyp >/dev/null 2>&1 \
        || { echo "MISSING hyp in ${RUN}"; FAILED=1; }
done

# 5. No credential left in the copies (the known patterns of the four redacted files).
if grep -rn --exclude=README.md -E "mysql -u [a-z]+ -p'[^<]|DBpass='[^<]|password='[^<]" "${REF}" >/dev/null; then
    echo "CREDENTIAL found under ${REF}"
    FAILED=1
fi

if [[ "${FAILED}" -eq 0 ]]; then
    echo "check-reference: OK"
fi
exit "${FAILED}"
