FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates cmake ninja-build git python3 \
    libsdl2-dev libgl1-mesa-dev libegl1-mesa-dev libgl1-mesa-dri \
    liblzma-dev liblzo2-dev zlib1g-dev libpng-dev libcurl4-openssl-dev \
    libfreetype6-dev libfontconfig1-dev libharfbuzz-dev libicu-dev \
    libopusfile-dev libfluidsynth-dev xvfb xauth mesa-utils \
    && rm -rf /var/lib/apt/lists/*

ENV LIBGL_ALWAYS_SOFTWARE=1
WORKDIR /workspace
