# yanll: NonLinLoc built from the upstream repository at a pinned commit, plus the yanll
# scripts. Nothing of a site is in the image: the configuration (station catalog and
# control-file templates) is mounted read-only at /config, grids and model bodies live
# in a volume at /data. The contract is docs/configuration.md.

# The author does not publish releases: `main` is the code, pinned here by SHA.
# Bump it on purpose, in its own commit, with the comparison report rerun.
ARG NLL_REPO=https://github.com/ut-beg-texnet/NonLinLoc
ARG NLL_COMMIT=7a62fa46eff682083352a2ca28e63a4f415d941b

FROM debian:bookworm-slim AS build
ARG NLL_REPO
ARG NLL_COMMIT

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
ARG NLL_REPO
ARG NLL_COMMIT
# Set by the CI when it publishes; the defaults mark a local build.
ARG SOURCE=https://github.com/INGV/yanll
ARG REVISION=local
ARG VERSION=dev

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

# CMake puts the executables in src/bin. The four programs a location uses, plus
# Time2EQ to synthesize the observations of a test event.
COPY --from=build /nll/src/bin/NLLoc /nll/src/bin/Vel2Grid /nll/src/bin/Grid2Time \
                  /nll/src/bin/GridCascadingDecimate /nll/src/bin/Time2EQ /opt/nll/bin/
COPY bin/ /opt/yanll/bin/

ENV PATH="/opt/yanll/bin:/opt/nll/bin:${PATH}" \
    YANLL_DATA=/data \
    YANLL_CONFIG=/config

# NonLinLoc is GPL-3: the labels record which sources, at which commit, the image was
# built from, for the image and for NLL.
LABEL org.opencontainers.image.title="yanll" \
      org.opencontainers.image.description="NonLinLoc as a containerized JSON-in, JSON-out locator" \
      org.opencontainers.image.source="${SOURCE}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.version="${VERSION}" \
      it.ingv.yanll.nonlinloc.source="${NLL_REPO}" \
      it.ingv.yanll.nonlinloc.revision="${NLL_COMMIT}"

VOLUME /data
WORKDIR /data
