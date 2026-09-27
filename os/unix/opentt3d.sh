#!/bin/sh
# Resolve bundled transitive dependencies as well as the executable's RUNPATH.
set -eu
directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export LD_LIBRARY_PATH="$directory/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$directory/opentt3d" "$@"
