"""Deterministic seeded generator for Python↔TS differential fuzzing.

Emits N random but valid inputs covering the chord-suffix grammar broadly,
biased toward known-tricky zones (aug5+alt, sus variants, slash, extensions).

Usage:
    python conformance/music-dsl/fuzz/gen.py [seed] [N]
    # defaults: seed=1, N=500

Output: conformance/music-dsl/fuzz/inputs.json
Each record is one of:
    {"kind": "chord",                "input": "<chord_string>"}
    {"kind": "numeric",              "input": "<numeric_string>"}
    {"kind": "numeric_from_chord",   "key_root": "<note>", "chord": "<chord_string>", "substitution": <bool>}
"""

import json
import random
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "inputs.json"

# ---------------------------------------------------------------------------
# Grammar constants
# ---------------------------------------------------------------------------

# All 17 chromatic note values (including enharmonics)
ROOTS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]
# Simpler flat-only roots for key_root (used in numeric_from_chord)
KEY_ROOTS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

# Triad tokens (including empty = major)
TRIADS = ["", "-", "h", "o", "+", "sus", "sus2", "sus4"]

# Seventh tokens
SEVENTHS = ["", "^7", "7", "^"]

# Extension tokens (individual)
EXTENSIONS = ["b9", "#9", "b9#9", "11", "#11", "b13", "13", "add9", "6", "69"]

# Special suffixes that must come before extensions in a chord string
ALT_SUFFIX = "alt"
AUG5_SUFFIX = "+"  # aug5 after seventh

# Roman numeral roots (ScaleDegree values)
SCALE_DEGREE_ROOTS = [
    "I", "i", "bII", "bii", "II", "ii", "bIII", "biii", "III", "iii",
    "IV", "iv", "#IV", "#iv", "bV", "bv", "V", "v", "bVI", "bvi",
    "VI", "vi", "bVII", "bvii", "VII", "vii",
]

# Sharp-prefixed roman degrees (less common, still in grammar)
SHARP_DEGREE_ROOTS = ["#I", "#i", "#II", "#ii", "#IV", "#iv", "#V", "#v", "#VI", "#vi"]


# ---------------------------------------------------------------------------
# Grammar builders
# ---------------------------------------------------------------------------

def _build_chord_string(rng: random.Random) -> str:
    """Build one chord string from the grammar.

    Bias: aug5+alt combos get extra weight (2× selection), sus positions 4×.
    """
    root = rng.choice(ROOTS)
    triad = rng.choice(TRIADS + TRIADS[:4])  # bias toward non-sus triads slightly

    # Seventh selection — sus chords can't have 7th+alt in some combos but
    # we still generate them to capture error cases.
    seventh = rng.choice(SEVENTHS)

    # Normalize ^ → ^7 as the grammar does
    if seventh == "^":
        seventh = "^7"

    aug5 = ""
    alt_flag = False

    is_sus = triad in ("sus", "sus2", "sus4")

    # aug5 is only valid after a 7th token (not for sus chords)
    if not is_sus and seventh in ("7", "^7", "^") and rng.random() < 0.12:
        aug5 = "+"

    # alt: cannot modify sus chords; needs 7th
    if not is_sus and rng.random() < 0.10:
        alt_flag = True
        seventh = "7"  # alt forces seventh=7

    # Extensions (skip for sus+alt combos that would be invalid)
    extensions = ""
    if not alt_flag and rng.random() < 0.35:
        n_ext = rng.randint(1, 2)
        chosen = rng.sample(EXTENSIONS, min(n_ext, len(EXTENSIONS)))
        extensions = "".join(chosen)

    suffix = triad + seventh + aug5 + (ALT_SUFFIX if alt_flag else "") + extensions
    return root + suffix


def _build_numeric_string(rng: random.Random) -> str:
    """Build one numeric chord string from the grammar.

    Covers: roman numeral roots, b/# prefixes, same triads/sevenths/extensions,
    leading-s substitution, slash chords.
    """
    # Bias: 80% standard SCALE_DEGREE_ROOTS, 20% SHARP_DEGREE_ROOTS
    if rng.random() < 0.8:
        root = rng.choice(SCALE_DEGREE_ROOTS)
    else:
        root = rng.choice(SHARP_DEGREE_ROOTS)

    triad = rng.choice(TRIADS)
    seventh = rng.choice(SEVENTHS)
    if seventh == "^":
        seventh = "^7"

    aug5 = ""
    alt_flag = False
    is_sus = triad in ("sus", "sus2", "sus4")

    if not is_sus and seventh in ("7", "^7") and rng.random() < 0.10:
        aug5 = "+"

    if not is_sus and rng.random() < 0.08:
        alt_flag = True
        seventh = "7"

    extensions = ""
    if not alt_flag and rng.random() < 0.30:
        n_ext = rng.randint(1, 2)
        chosen = rng.sample(EXTENSIONS, min(n_ext, len(EXTENSIONS)))
        extensions = "".join(chosen)

    suffix = triad + seventh + aug5 + (ALT_SUFFIX if alt_flag else "") + extensions
    numerator = root + suffix

    # Leading "s" substitution (10% of numeric inputs)
    if rng.random() < 0.10:
        numerator = "s" + numerator

    # Slash chord: 15% of numeric inputs (denominator = simple degree, no leading s)
    if rng.random() < 0.15:
        denom_root = rng.choice(SCALE_DEGREE_ROOTS)
        denom_triad = rng.choice(["", "-", ""])
        denom_seventh = rng.choice(["", "7", "^7", ""])
        numerator = numerator + "/" + denom_root + denom_triad + denom_seventh

    return numerator


def _build_numeric_from_chord(rng: random.Random) -> dict:
    """Build one numeric_from_chord triple: (key_root, chord, substitution)."""
    key_root = rng.choice(KEY_ROOTS)
    chord = _build_chord_string(rng)
    substitution = rng.random() < 0.4  # 40% substitution=True
    return {"kind": "numeric_from_chord", "key_root": key_root, "chord": chord, "substitution": substitution}


# ---------------------------------------------------------------------------
# Bias batches — known-tricky inputs always included regardless of sampling
# ---------------------------------------------------------------------------

BIAS_CHORDS = [
    # aug5+alt (the known C7+alt divergence trigger)
    "C7+", "G7+", "Ab7+", "F7+",
    "C7alt", "G7alt", "Bb7alt",
    "C7+alt",  # aug5 then alt — likely invalid but captured
    # sus positions
    "Csus", "Csus4", "Csus2", "C4",
    "C9sus", "C9sus4", "C7susb9", "C7b9sus", "Csus7b9", "Csus9",
    "D9sus", "G9sus", "Fsus", "Bbsus",
    # enharmonic roots
    "C#-7", "Db^7", "Cb", "B#", "Fb", "E#", "F#7", "G#-7",
    # extension combos
    "C^7#11", "C13", "C7b9", "Cadd9", "C69",
    "C7b9#11", "C-7b9", "C7#9", "C7b9#9", "C-^7",
    # error territory (captured as errors)
    "xyzzy", "VIII", "C|D", "B#b9", "Cadd²",
]

BIAS_NUMERICS = [
    "ii-7", "V7", "I^7", "bVI^7", "#ivo7", "sV7",
    "V7/V", "ii-7/IV",
    # tricky combinations
    "bVII7", "bII7", "IV^7", "ii-^7",
    "sI7", "sbII7",
    "#IV7", "bVI-7",
    "V7/ii", "V7/IV", "V7/bVI",
]

BIAS_FROM_CHORD = [
    # substitution=True anchors from existing conformance cases
    ("C", "E-7", True), ("C", "E-7", False),
    ("C", "Ab-7", True), ("C", "Ab-7", False),
    ("C", "Db7", True),
    ("F#", "C7", True),   # known IncorrectHarmonicFunctionError
    # aug5 + substitution
    ("C", "G7+", False), ("C", "G7+", True),
    ("C", "C7alt", False), ("C", "C7alt", True),
    # enharmonic key roots
    ("Gb", "Db7", False), ("Eb", "Bb7", False),
]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(seed: int = 1, n: int = 500) -> list[dict]:
    """Generate a deterministic batch of fuzz inputs.

    Distribution target (flexible):
      ~40% chord, ~30% numeric, ~30% numeric_from_chord
    """
    rng = random.Random(seed)
    records: list[dict] = []

    # Always include the bias batches first
    for c in BIAS_CHORDS:
        records.append({"kind": "chord", "input": c})
    for nm in BIAS_NUMERICS:
        records.append({"kind": "numeric", "input": nm})
    for key_root, chord, sub in BIAS_FROM_CHORD:
        records.append({"kind": "numeric_from_chord", "key_root": key_root, "chord": chord, "substitution": sub})

    bias_count = len(records)
    remaining = max(0, n - bias_count)

    # Randomly fill the remainder
    for _ in range(remaining):
        roll = rng.random()
        if roll < 0.40:
            records.append({"kind": "chord", "input": _build_chord_string(rng)})
        elif roll < 0.70:
            records.append({"kind": "numeric", "input": _build_numeric_string(rng)})
        else:
            records.append(_build_numeric_from_chord(rng))

    return records


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 500

    records = generate(seed, n)
    OUT.write_text(json.dumps(records, indent=2) + "\n")

    counts = {}
    for r in records:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    print(f"Generated {len(records)} inputs (seed={seed}, N={n}) -> {OUT}")
    for kind, c in sorted(counts.items()):
        print(f"  {kind}: {c}")
