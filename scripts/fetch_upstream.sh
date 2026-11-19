#!/bin/sh
# Fetch the upstream benchmark repositories at the commits this analysis used.
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

# Verdicts published: reproduced and measured by `sc-zprime run`.
fetch scbench 106726f432e0221a3fdbf9ef8e39b21f638f9b60
fetch spatialbench baa9841efc99fa03b2f9ec25684c8ec52a2245df
# Transcripts and grader configs published: graded by `sc-zprime regrade`.
fetch variantbench 96a26565d7ff08961a2bbdd1061cd5957a9b3692
fetch txbench-pp 920bff72157cb2a6106ff4f534f160eccca8ad85
# Counted by `sc-zprime inventory` only.
fetch epibench 46c69cba20b41c6da337766f9b24df3ab4bf7687
fetch metagenomicsbench 661be73c5255f11b4d5973afbbfb6f4501646b5d
fetch neurobench 804b78c5e8aca83cee3ccfb1338280d5891800e4
fetch oncologybench 96eb31b7e5611dd8f5c178d9b962d6e0cc1a4c76
fetch rarediseasebench f296e7f03f0957668de8e3fc334f2cb1d4ea6973
fetch scbench-long b3991d83db2fc51b735cbc978d09c9e8a141ea20
fetch spatialbench-long b693be22d32755c2c0c3c376a8b3b71d226e2685
fetch tissuemicroscopybench 9ec8ac7a3a5dcdad00f51d73a263836f8fb599fe
fetch txBench-antibody-development d9a81be590073d542f35fbac1bd61df3f4368395
fetch txbench-antibody-discovery b4a28e48202da521d6aeea82613c30fd4784e1ec
fetch txbench-oligo-discovery b757f9a455a5356cf4a973dd3161b2b664439a9d
# The public evaluation tool. Read for its graders and for the agent environment file that
# docs/SPATIALBENCH.md cites. It is not a benchmark, so `sc-zprime inventory` is told to skip it.
fetch latch-eval-tools 0d7983126cbc6e298b9865de32b1f0d988aee1a5
