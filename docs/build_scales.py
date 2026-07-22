#!/usr/bin/env python3
"""Generate the scale-catalog table in docs/scales.md from the live music_dsl catalog.

The table is the single hardest thing in these docs to keep correct by hand — 39
scales, each with a pitch-class formula that must match the conformance corpus. So
we don't keep it by hand: this script imports the real `Scales` enum and decodes
each mask with the library's own `contains`, then rewrites the block between the
`<!-- BEGIN GENERATED SCALES -->` / `<!-- END GENERATED SCALES -->` markers in
scales.md. Run it before `mkdocs build`; CI runs it too, so the published table
can never drift from the source catalog.

Usage:  python docs/build_scales.py        # rewrite in place
        python docs/build_scales.py --check # exit 1 if the table is stale
"""
from __future__ import annotations

import sys
from pathlib import Path

from music_dsl.encode import Scales, contains

BEGIN = "<!-- BEGIN GENERATED SCALES -->"
END = "<!-- END GENERATED SCALES -->"
SCALES_MD = Path(__file__).resolve().parent / "scales.md"


def pitch_classes(scale: Scales) -> str:
    """Semitones-above-tonic present in the scale, via the library's own membership."""
    return " ".join(str(pc) for pc in range(12) if contains(scale, pc))


def render_table() -> str:
    rows = list(Scales)
    functional = [s for s in rows if s.value.supports_diatonic_function]
    symmetric = [s for s in rows if not s.value.supports_diatonic_function]

    def table(scales: list[Scales]) -> str:
        head = "| Scale | Category | Semitones (from tonic) | Diatonic queries |\n"
        head += "|-------|----------|------------------------|------------------|\n"
        body = "".join(
            f"| {s.value.name} | `{s.value.category}` | {pitch_classes(s)} | "
            f"{'✅ defined' if s.value.supports_diatonic_function else '⛔ refuses'} |\n"
            for s in scales
        )
        return head + body

    out = [
        BEGIN,
        f"*{len(rows)} scales — generated from the `music_dsl` catalog, so this table "
        f"cannot drift from the conformance corpus.*",
        "",
        f"### Functional scales ({len(functional)})",
        "",
        "`contains` **and** `is_diatonic` / harmonic-function queries are defined.",
        "",
        table(functional).rstrip(),
        "",
        f"### Symmetric / atonal scales ({len(symmetric)})",
        "",
        "Membership (`contains`) works; functional queries **refuse** "
        "(Python raises, TS throws, Rust `Err`).",
        "",
        table(symmetric).rstrip(),
        END,
    ]
    return "\n".join(out)


def main() -> int:
    check = "--check" in sys.argv
    table = render_table()

    # Self-check: one row per scale, guarding against a decode/format regression.
    n_rows = table.count("| `")  # each data row has a `category` code span
    assert n_rows == len(list(Scales)) == 39, f"expected 39 rows, rendered {n_rows}"

    text = SCALES_MD.read_text()
    if BEGIN not in text or END not in text:
        print(f"error: markers not found in {SCALES_MD}", file=sys.stderr)
        return 2
    pre = text[: text.index(BEGIN)]
    post = text[text.index(END) + len(END) :]
    new = pre + table + post

    if check:
        if new != text:
            print(f"stale: {SCALES_MD} — run `python docs/build_scales.py`", file=sys.stderr)
            return 1
        print("scales table current")
        return 0

    SCALES_MD.write_text(new)
    print(f"wrote {len(list(Scales))} scales to {SCALES_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
