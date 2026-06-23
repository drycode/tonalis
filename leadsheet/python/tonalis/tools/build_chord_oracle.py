"""FROZEN — do not re-run (Task-4 retirement).

The old ``chord_grammar`` regex was retired in Task 4, replaced by a shim that re-exports
``tonalis.chords.is_valid_chord``.  Because the OLD validator no longer exists, this builder
has no independent "old" verdict to compare against and **cannot produce a meaningful oracle**.
Running it would overwrite ``tests/fixtures/chord_oracle.json`` with identical old/new verdicts
(same function), silently destroying the frozen divergence record (``C7777 = true``) that
``test_chord_reconciliation.py`` enforces.

The committed ``chord_oracle.json`` is the **permanent frozen snapshot** of the pre-retirement
``chord_grammar`` verdicts.  It is the ground truth; do not regenerate it.

This builder is kept for historical/reference purposes only.  It will refuse to run and will
print a clear explanation to stderr before exiting with code 2.

CI never runs this — it consumes the committed fixture only (see
``tests/test_chord_reconciliation.py``).

Corpus source
-------------
The token universe is the **conformance corpus** (``conformance/dsl-core/cases/**/*.json``):
every ``"chord"`` string anywhere under a case's ``expect.ast``, PLUS every chord-looking
token inside the compound ``"alt"`` strings (``"(A4 Gh7)"`` -> ``A4``, ``Gh7``). This is the
corpus the Phase-1 debate swept to find the divergences, and it carries clean chord tokens
only (no iReal control junk), so it is the reliable, reproducible oracle source.

The iReal **sqlite** corpus is intentionally NOT used here. Its real shape is Core Data
(table ``SCRUBBED``, column ``SCRUBBED``) holding RAW SCRUBBED iReal — markers, time
signatures, ``x`` repeats, ``N1``/``N2`` endings, ``<Fine>``/``<D.C...>`` glued to chords —
which cannot be split into chord tokens without the SCRUBBED reader. SCRUBBED is not a
dependency of this standalone repo, and the monorepo's copy ships the OLD ``music_dsl`` (no
``X4`` teaching), so importing it would give wrong verdicts. The conformance corpus is what
surfaced every divergence, so the sqlite breadth is a deliberate, documented residual.
"""

import json
import re
import sys
from pathlib import Path

from tonalis import chord_grammar  # OLD validator (retired after Task 4, present here)
from tonalis import chords as new_chords  # NEW MusicDSL-backed wrapper

# this file: <repo>/leadsheet/python/tonalis/tools/build_chord_oracle.py
#   parents[0]=tools  parents[1]=tonalis  parents[2]=python  parents[3]=leadsheet  parents[4]=repo
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[4]
_CASES_DIR = _REPO_ROOT / "conformance" / "dsl-core" / "cases"
_FIXTURE = _HERE.parents[2] / "tests" / "fixtures" / "chord_oracle.json"

# A chord-looking token: starts with a note letter (opt. accidental) or a slash-bass.
_CHORDISH = re.compile(r"^(?:[A-G][b#]?.*|/[A-G][b#]?|N\.C\.|n)$")


def _walk_chord_values(node, out: set) -> None:
    """Collect every ``"chord"`` string value anywhere in the AST, and every chord-looking
    token inside an ``"alt"`` string (alts are space-separated compound chords in parens)."""
    if isinstance(node, dict):
        for key, val in node.items():
            if key == "chord" and isinstance(val, str):
                out.add(val)
            elif key == "alt" and isinstance(val, str):
                for raw in val.strip("()").split():
                    tok = raw.strip()
                    if tok and _CHORDISH.match(tok):
                        out.add(tok)
            else:
                _walk_chord_values(val, out)
    elif isinstance(node, list):
        for item in node:
            _walk_chord_values(item, out)


def _corpus_tokens() -> list:
    toks: set = set()
    for case_path in sorted(_CASES_DIR.rglob("*.json")):
        case = json.loads(case_path.read_text(encoding="utf-8"))
        _walk_chord_values(case.get("expect", {}).get("ast"), toks)
    toks.discard(None)
    return sorted(toks)


def main() -> int:
    # Guard: detect that chord_grammar is now the Task-4 shim (re-exports tonalis.chords).
    # If old and new are the same function, there is no independent OLD validator left to sweep
    # against, and running the builder would silently overwrite the frozen fixture with
    # all-identical verdicts, destroying the C7777=true divergence record.
    if chord_grammar.is_valid_chord is new_chords.is_valid_chord:
        print(
            "ERROR: The old chord_grammar regex was retired in Task 4; chord_grammar.is_valid_chord\n"
            "is now a shim that re-exports tonalis.chords.is_valid_chord.  There is no independent\n"
            "OLD validator remaining to compare against.\n"
            "\n"
            "The committed tests/fixtures/chord_oracle.json is the PERMANENT FROZEN record of the\n"
            "pre-retirement chord_grammar verdicts.  Re-running this builder cannot produce an\n"
            "honest oracle and would destroy the C7777=true divergence that the reconciliation test\n"
            "enforces.  Do NOT regenerate.\n"
            "\n"
            "This builder is kept for historical/reference purposes only.",
            file=sys.stderr,
        )
        return 2

    oracle, diverge = {}, []
    for tok in _corpus_tokens():
        old = chord_grammar.is_valid_chord(tok)
        new = new_chords.is_valid_chord(tok)
        oracle[tok] = old
        if old != new:
            diverge.append((tok, old, new))

    _FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    _FIXTURE.write_text(
        json.dumps(oracle, indent=0, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"oracle: {len(oracle)} tokens -> {_FIXTURE.relative_to(_REPO_ROOT)}")
    if diverge:
        print(f"\n{len(diverge)} DIVERGENCES (token, old, new):")
        for d in diverge:
            print("   ", d)
        return 1
    print("zero divergences — new wrapper matches the old grammar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
