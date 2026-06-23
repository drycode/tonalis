#!/usr/bin/env bash
# 3-way Python↔TS↔Rust differential fuzzer runner.
# Usage:
#   ./conformance/music-dsl/fuzz/run_fuzz.sh [SEED] [N]
#   # defaults: SEED=1, N=500
#
# Steps:
#   1. Generate seeded inputs via gen.py
#   2. Run Python oracle via oracle.py
#   3. Build + run Rust fuzz_runner (produces rust_out.json)
#   4. Run vitest 3-way differential suite (Python vs TS vs Rust)
#
# Exit code 0 = 0 divergences, non-zero = divergences or setup failure.

set -euo pipefail

SEED="${1:-1}"
N="${2:-500}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FUZZ_DIR="${REPO_ROOT}/conformance/music-dsl/fuzz"
RUST_DIR="${REPO_ROOT}/music-dsl/rust"
TS_DIR="${REPO_ROOT}/music-dsl/ts"

echo "=== music-dsl 3-way differential fuzzer (seed=${SEED}, N=${N}) ==="

echo ""
echo "--- Step 1: Generate inputs ---"
(cd "${REPO_ROOT}" && python conformance/music-dsl/fuzz/gen.py "${SEED}" "${N}")

echo ""
echo "--- Step 2: Python oracle ---"
(cd "${REPO_ROOT}" && python conformance/music-dsl/fuzz/oracle.py)

echo ""
echo "--- Step 3: Rust fuzz runner ---"
(cd "${RUST_DIR}" && CARGO_MANIFEST_DIR="${RUST_DIR}" cargo run --bin fuzz_runner --quiet)

echo ""
echo "--- Step 4: 3-way differential (vitest) ---"
(cd "${TS_DIR}" && \
  NODE_PATH=node_modules node node_modules/.bin/vitest run \
    --config "${FUZZ_DIR}/vitest.fuzz.config.ts" \
    --reporter=verbose 2>&1 | tail -20)

echo ""
echo "=== Fuzzer run complete: seed=${SEED} N=${N} ==="
