#!/usr/bin/env bash
#
# build_api.sh — generate the per-language API references for the Tonalis docs.
#
# Repeatable, idempotent, and best-effort: each port's generator is run only if
# its toolchain is available. A missing toolchain (pdoc / typedoc / cargo) is not
# a failure — the port is skipped and a small placeholder index is written so the
# mkdocs site still builds and the API-hub links resolve.
#
# Output (all git-ignored, see .gitignore):
#   docs/api/python/  <- pdoc  (music_dsl + tonalis)
#   docs/api/ts/      <- typedoc (music-dsl/ts + tonalis/ts)
#   docs/api/rust/    <- cargo doc --no-deps (music-dsl/rust + tonalis/rust)
#
# Usage:  bash docs/build_api.sh   (run from anywhere; paths are repo-relative)
set -euo pipefail

# Resolve repo root from this script's location (docs/ is a direct child).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
API="$ROOT/docs/api"

placeholder() {
  # $1 = output dir, $2 = human label, $3 = reason
  local dir="$1" label="$2" reason="$3"
  mkdir -p "$dir"
  cat > "$dir/index.html" <<HTML
<!doctype html>
<meta charset="utf-8">
<title>${label} API — not generated</title>
<h1>${label} API reference</h1>
<p>This API reference was not generated: ${reason}.</p>
<p>Run <code>bash docs/build_api.sh</code> with the ${label} toolchain installed
to populate this page.</p>
HTML
  echo "  -> placeholder written to ${dir#$ROOT/}"
}

echo "== Python (pdoc) =="
if command -v pdoc >/dev/null 2>&1; then
  # music_dsl + tonalis must be importable (installed editable) for pdoc.
  rm -rf "$API/python"
  mkdir -p "$API/python"
  if pdoc -o "$API/python" music_dsl tonalis 2>/dev/null; then
    echo "  -> docs/api/python/"
  else
    placeholder "$API/python" "Python" "pdoc ran but the packages are not importable (pip install -e ./music-dsl/python ./tonalis/python)"
  fi
else
  placeholder "$API/python" "Python" "pdoc not installed (pip install pdoc)"
fi

echo "== TypeScript (typedoc) =="
gen_ts() {
  # $1 = package dir, $2 = output subdir
  local pkg="$1" out="$2"
  if [ -d "$ROOT/$pkg/node_modules" ] && [ -x "$ROOT/$pkg/node_modules/.bin/typedoc" ]; then
    ( cd "$ROOT/$pkg" && ./node_modules/.bin/typedoc --out "$API/ts/$out" src/index.ts ) \
      && echo "  -> docs/api/ts/$out/" && return 0
  fi
  return 1
}
if command -v npx >/dev/null 2>&1 || [ -d "$ROOT/music-dsl/ts/node_modules" ]; then
  mkdir -p "$API/ts"
  ok=0
  gen_ts "music-dsl/ts" "music-dsl" && ok=1 || true
  gen_ts "tonalis/ts" "tonalis" && ok=1 || true
  if [ "$ok" -eq 0 ]; then
    placeholder "$API/ts" "TypeScript" "typedoc unavailable (cd music-dsl/ts && npm ci; npm i -D typedoc)"
  else
    # Landing page linking the two TS packages.
    cat > "$API/ts/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>TypeScript API</title>
<h1>TypeScript API reference</h1>
<ul>
  <li><a href="music-dsl/index.html">music-dsl</a> — theory core</li>
  <li><a href="tonalis/index.html">leadsheet (tonalis)</a> — lead-sheet language</li>
</ul>
HTML
  fi
else
  placeholder "$API/ts" "TypeScript" "node/typedoc unavailable"
fi

echo "== Rust (cargo doc) =="
gen_rust() {
  # $1 = crate dir
  local crate="$1"
  ( cd "$ROOT/$crate" && cargo doc --no-deps --target-dir "$API/rust/_target-$(basename "$crate")" ) >/dev/null 2>&1
}
if command -v cargo >/dev/null 2>&1; then
  mkdir -p "$API/rust"
  # cargo doc emits into <target>/doc; we point each crate at a scratch target and
  # then copy the rendered doc/ trees together under docs/api/rust/.
  ok=0
  for crate in music-dsl/rust tonalis/rust; do
    if gen_rust "$crate"; then
      name="$(basename "$(dirname "$ROOT/$crate")")-$(basename "$crate")"
      # Copy the generated doc tree (crate-name subdirs live inside doc/).
      cp -R "$API/rust/_target-$(basename "$crate")/doc/." "$API/rust/" 2>/dev/null || true
      ok=1
    fi
  done
  rm -rf "$API/rust"/_target-* 2>/dev/null || true
  if [ "$ok" -eq 0 ]; then
    placeholder "$API/rust" "Rust" "cargo doc failed"
  elif [ ! -f "$API/rust/index.html" ]; then
    # cargo doc doesn't emit a top-level index.html; write one that links the crates.
    cat > "$API/rust/index.html" <<'HTML'
<!doctype html><meta charset="utf-8"><title>Rust API</title>
<h1>Rust API reference</h1>
<ul>
  <li><a href="tonalis/index.html">tonalis</a> (leadsheet crate)</li>
</ul>
<p>Each crate's docs are in its own subdirectory (crate name).</p>
HTML
  fi
else
  placeholder "$API/rust" "Rust" "cargo not installed"
fi

echo "Done. API references under docs/api/ (git-ignored)."
