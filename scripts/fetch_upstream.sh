#!/bin/sh
# Fetch the upstream benchmark repository at the commit this analysis used.
#
#   scripts/fetch_upstream.sh [target-dir]      default: ../upstream
#
# The checkout is read as data. Nothing in it is executed. Keep it outside
# this repository: it contains benchmark task files that carry a canary
# string and must not be redistributed (see docs/DATA_POLICY.md).
set -eu

target="${1:-../upstream}"
mkdir -p "$target"

fetch() {
    name="$1"; commit="$2"
    dir="$target/$name"
    if [ ! -d "$dir/.git" ]; then
        git init -q "$dir"
        git -C "$dir" remote add origin "https://github.com/latchbio/$name.git"
    fi
    git -C "$dir" -c core.hooksPath=/dev/null fetch -q --depth 1 origin "$commit"
    git -C "$dir" -c core.hooksPath=/dev/null checkout -q FETCH_HEAD
    echo "$name at $(git -C "$dir" rev-parse --short HEAD)"
}

fetch scbench 106726f432e0221a3fdbf9ef8e39b21f638f9b60
