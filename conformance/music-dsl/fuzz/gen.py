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
    {"kind": "chord_pitches",        "chord": "<chord_string>", "octave": 4}
    {"kind": "scale_pitches",        "root": "<note>", "scale": "<scale_name>", "octave": 4}
    {"kind": "scale_degree_pitch",   "degree": "<degree_value>", "key_root": "<note>", "octave": 4}
    {"kind": "note_to_midi",         "note": "<note>", "octave": <int>}
    {"kind": "modulate",             "semitones": <int>, "note": "<note_or_degree>"}
    {"kind": "is_diatonic",          "root": "<note>", "scale": "<scale_name>", "chord": "<chord_string>"}
    {"kind": "chord_in_key",         "numeric": "<numeric_string>", "key_root": "<note>"}

Intentional omissions:
    - midi_to_hz: float output — rounding divergence risk across Python/TS/Rust floating-point
      representations makes cross-port equality assertions unreliable.
    - parse_measure: corpus-pinned edge cases (repeats, section markers) are integration-level
      concerns; generative coverage would require a separate measure grammar generator and would
      hit existing known divergences in the measure parser that are not part of the realize/
      transactions scope.
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

# Scale names for realize/transactions ops
SCALE_NAMES = ["Major", "Minor", "HarmonicMinor"]

# ScaleDegree values (major variants)
SCALE_DEGREES_MAJOR = ["I", "bII", "II", "bIII", "III", "IV", "bV", "V", "bVI", "VI", "bVII", "VII"]
# ScaleDegree values (minor variants)
SCALE_DEGREES_MINOR = ["i", "bii", "ii", "biii", "iii", "iv", "bv", "v", "bvi", "vi", "bvii", "vii"]
# All scale degree values (all 26)
ALL_SCALE_DEGREE_VALUES = SCALE_DEGREES_MAJOR + SCALE_DEGREES_MINOR

# Semitone offsets for modulate
SEMITONE_OFFSETS = list(range(12))


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


def _build_chord_pitches(rng: random.Random) -> dict:
    """Build one chord_pitches record. Only valid chord strings (no deliberate errors)."""
    chord = _build_chord_string(rng)
    return {"kind": "chord_pitches", "chord": chord, "octave": 4}


def _build_scale_pitches(rng: random.Random) -> dict:
    """Build one scale_pitches record."""
    root = rng.choice(KEY_ROOTS)
    scale = rng.choice(SCALE_NAMES)
    return {"kind": "scale_pitches", "root": root, "scale": scale, "octave": 4}


def _build_scale_degree_pitch(rng: random.Random) -> dict:
    """Build one scale_degree_pitch record."""
    degree = rng.choice(ALL_SCALE_DEGREE_VALUES)
    key_root = rng.choice(KEY_ROOTS)
    return {"kind": "scale_degree_pitch", "degree": degree, "key_root": key_root, "octave": 4}


def _build_note_to_midi(rng: random.Random) -> dict:
    """Build one note_to_midi record with octave in range 2–6."""
    note = rng.choice(ROOTS)
    octave = rng.randint(2, 6)
    return {"kind": "note_to_midi", "note": note, "octave": octave}


def _build_modulate(rng: random.Random) -> dict:
    """Build one modulate record: note-or-degree × semitone-offset."""
    semitones = rng.choice(SEMITONE_OFFSETS)
    # 50% note, 50% scale degree
    if rng.random() < 0.5:
        note = rng.choice(ROOTS)
    else:
        note = rng.choice(ALL_SCALE_DEGREE_VALUES)
    return {"kind": "modulate", "semitones": semitones, "note": note}


def _build_is_diatonic(rng: random.Random) -> dict:
    """Build one is_diatonic record."""
    root = rng.choice(KEY_ROOTS)
    scale = rng.choice(SCALE_NAMES)
    chord = _build_chord_string(rng)
    return {"kind": "is_diatonic", "root": root, "scale": scale, "chord": chord}


def _build_chord_in_key(rng: random.Random) -> dict:
    """Build one chord_in_key record using the numeric grammar."""
    numeric = _build_numeric_string(rng)
    key_root = rng.choice(KEY_ROOTS)
    return {"kind": "chord_in_key", "numeric": numeric, "key_root": key_root}


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

# Bias batches for realize ops — known-tricky cases
BIAS_CHORD_PITCHES = [
    # dim7 rule
    {"kind": "chord_pitches", "chord": "Co7", "octave": 4},
    {"kind": "chord_pitches", "chord": "Ch7", "octave": 4},
    # aug triad
    {"kind": "chord_pitches", "chord": "C+", "octave": 4},
    # extensions
    {"kind": "chord_pitches", "chord": "C7alt", "octave": 4},
    {"kind": "chord_pitches", "chord": "C7b9", "octave": 4},
    {"kind": "chord_pitches", "chord": "C^7#11", "octave": 4},
    # enharmonic roots
    {"kind": "chord_pitches", "chord": "Db^7", "octave": 4},
    {"kind": "chord_pitches", "chord": "C#-7", "octave": 4},
]

BIAS_SCALE_PITCHES = [
    {"kind": "scale_pitches", "root": "C",  "scale": "Major",        "octave": 4},
    {"kind": "scale_pitches", "root": "A",  "scale": "Minor",        "octave": 4},
    {"kind": "scale_pitches", "root": "A",  "scale": "HarmonicMinor","octave": 4},
    {"kind": "scale_pitches", "root": "Bb", "scale": "Major",        "octave": 4},
    {"kind": "scale_pitches", "root": "Gb", "scale": "Major",        "octave": 4},
]

BIAS_SCALE_DEGREE_PITCH = [
    {"kind": "scale_degree_pitch", "degree": "I",    "key_root": "C", "octave": 4},
    {"kind": "scale_degree_pitch", "degree": "V",    "key_root": "C", "octave": 4},
    {"kind": "scale_degree_pitch", "degree": "bVII", "key_root": "C", "octave": 4},
    {"kind": "scale_degree_pitch", "degree": "i",    "key_root": "A", "octave": 4},
    {"kind": "scale_degree_pitch", "degree": "biii", "key_root": "F", "octave": 4},
]

BIAS_NOTE_TO_MIDI = [
    {"kind": "note_to_midi", "note": "C",  "octave": 4},  # middle C = 60
    {"kind": "note_to_midi", "note": "A",  "octave": 4},  # A4 = 69
    {"kind": "note_to_midi", "note": "B",  "octave": 2},  # low boundary
    {"kind": "note_to_midi", "note": "Db", "octave": 6},  # high, enharmonic
    {"kind": "note_to_midi", "note": "C#", "octave": 4},  # sharp root
]

BIAS_MODULATE = [
    # notes
    {"kind": "modulate", "semitones": 0,  "note": "C"},
    {"kind": "modulate", "semitones": 7,  "note": "C"},   # up a fifth
    {"kind": "modulate", "semitones": 11, "note": "Db"},  # wraps around
    # scale degrees
    {"kind": "modulate", "semitones": 5,  "note": "I"},   # IV
    {"kind": "modulate", "semitones": 7,  "note": "ii"},  # minor → vi
    {"kind": "modulate", "semitones": 0,  "note": "bVII"},
    {"kind": "modulate", "semitones": 3,  "note": "v"},
]

BIAS_IS_DIATONIC = [
    {"kind": "is_diatonic", "root": "C", "scale": "Major",        "chord": "C"},
    {"kind": "is_diatonic", "root": "C", "scale": "Major",        "chord": "G7"},
    {"kind": "is_diatonic", "root": "C", "scale": "Major",        "chord": "Db"},   # non-diatonic root
    {"kind": "is_diatonic", "root": "A", "scale": "Minor",        "chord": "E"},
    {"kind": "is_diatonic", "root": "A", "scale": "HarmonicMinor","chord": "E7"},
    {"kind": "is_diatonic", "root": "C", "scale": "Major",        "chord": "C7+"},  # aug, invalid grammar
]

BIAS_CHORD_IN_KEY = [
    {"kind": "chord_in_key", "numeric": "V7",     "key_root": "C"},
    {"kind": "chord_in_key", "numeric": "ii-7",   "key_root": "C"},
    {"kind": "chord_in_key", "numeric": "bVII7",  "key_root": "Bb"},
    {"kind": "chord_in_key", "numeric": "V7/V",   "key_root": "G"},
    {"kind": "chord_in_key", "numeric": "sV7",    "key_root": "C"},
]


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(seed: int = 1, n: int = 500) -> list[dict]:
    """Generate a deterministic batch of fuzz inputs.

    Distribution target (random fill after bias batches):
      ~15% chord, ~10% numeric, ~10% numeric_from_chord
      ~15% chord_pitches, ~10% scale_pitches, ~5% scale_degree_pitch, ~5% note_to_midi
      ~10% modulate, ~10% is_diatonic, ~5% chord_in_key
      (remaining ~5% chord)
    """
    rng = random.Random(seed)
    records: list[dict] = []

    # Always include all bias batches first (deterministic anchors)
    for c in BIAS_CHORDS:
        records.append({"kind": "chord", "input": c})
    for nm in BIAS_NUMERICS:
        records.append({"kind": "numeric", "input": nm})
    for key_root, chord, sub in BIAS_FROM_CHORD:
        records.append({"kind": "numeric_from_chord", "key_root": key_root, "chord": chord, "substitution": sub})
    records.extend(BIAS_CHORD_PITCHES)
    records.extend(BIAS_SCALE_PITCHES)
    records.extend(BIAS_SCALE_DEGREE_PITCH)
    records.extend(BIAS_NOTE_TO_MIDI)
    records.extend(BIAS_MODULATE)
    records.extend(BIAS_IS_DIATONIC)
    records.extend(BIAS_CHORD_IN_KEY)

    bias_count = len(records)
    remaining = max(0, n - bias_count)

    # Randomly fill the remainder
    # Cumulative thresholds:
    #   0.00–0.15 chord
    #   0.15–0.25 numeric
    #   0.25–0.35 numeric_from_chord
    #   0.35–0.50 chord_pitches
    #   0.50–0.60 scale_pitches
    #   0.60–0.65 scale_degree_pitch
    #   0.65–0.70 note_to_midi
    #   0.70–0.80 modulate
    #   0.80–0.90 is_diatonic
    #   0.90–0.95 chord_in_key
    #   0.95–1.00 chord (extra weight)
    for _ in range(remaining):
        roll = rng.random()
        if roll < 0.15:
            records.append({"kind": "chord", "input": _build_chord_string(rng)})
        elif roll < 0.25:
            records.append({"kind": "numeric", "input": _build_numeric_string(rng)})
        elif roll < 0.35:
            records.append(_build_numeric_from_chord(rng))
        elif roll < 0.50:
            records.append(_build_chord_pitches(rng))
        elif roll < 0.60:
            records.append(_build_scale_pitches(rng))
        elif roll < 0.65:
            records.append(_build_scale_degree_pitch(rng))
        elif roll < 0.70:
            records.append(_build_note_to_midi(rng))
        elif roll < 0.80:
            records.append(_build_modulate(rng))
        elif roll < 0.90:
            records.append(_build_is_diatonic(rng))
        elif roll < 0.95:
            records.append(_build_chord_in_key(rng))
        else:
            records.append({"kind": "chord", "input": _build_chord_string(rng)})

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
