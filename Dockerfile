# yanll: NonLinLoc built from the upstream repository at a pinned commit, plus the
# production model inputs and the scripts that generate the travel-time grids and run a
# location. Grids and the 3D model body live in a volume mounted at /data, never in
# the image.

FROM debian:bookworm-slim AS build

# The author does not publish releases: `main` is the code, pinned here by SHA.
# Bump it on purpose, in its own commit, with the comparison report rerun.
ARG NLL_REPO=https://github.com/ut-beg-texnet/NonLinLoc
ARG NLL_COMMIT=7a62fa46eff682083352a2ca28e63a4f415d941b

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git cmake gcc g++ make libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone "${NLL_REPO}" /nll \
    && cd /nll \
    && git checkout "${NLL_COMMIT}" \
    && cd src \
    && cmake . \
    && make -j"$(nproc)"

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

# CMake puts the executables in src/bin. Only the four programs the chain uses.
COPY --from=build /nll/src/bin/NLLoc /nll/src/bin/Vel2Grid /nll/src/bin/Grid2Time \
                  /nll/src/bin/GridCascadingDecimate /opt/nll/bin/
COPY --from=build /nll/src/GridLib.h /opt/nll/src/GridLib.h

# Production inputs, unchanged: 1D models with the zone table and corrections, 3D
# corrections, and the station snapshot.
COPY reference/production/opt/nll/run/modelli_20211027 /opt/yanll/models_1d
COPY reference/production/opt/nll/run/corrections_3d /opt/yanll/corrections_3d
COPY stations/fdsnws-station.txt /opt/yanll/stations/fdsnws-station.txt
COPY bin/ /opt/yanll/bin/

ENV PATH="/opt/yanll/bin:/opt/nll/bin:${PATH}" \
    YANLL_DATA=/data

VOLUME /data
WORKDIR /data
