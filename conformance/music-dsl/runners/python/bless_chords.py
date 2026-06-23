"""One-shot: generate and BLESS conformance/music-dsl/cases/chords/*.json from the frozen Python reference.

Run from the tonalis root:
    source .venv/bin/activate
    python conformance/music-dsl/runners/python/bless_chords.py

Each output file is written to conformance/music-dsl/cases/chords/<name>.json.
Expected values are determined by RUNNING the reference (parse_chord / encode_chord ops) —
NOT hand-authored — so blessed = correct oracle.

Error inputs are captured as {error: true} when InvalidChordStringException is raised.

Files produced:
    basic.json         -- canonical chord forms across roots
    sus_ambiguity.json -- C3 sus/augmented ambiguity batch (cross-port portability gate)
    extensions.json    -- extension parsing (add, 69, alt, aug5, multi-extension)
    enharmonic.json    -- flat/sharp root normalisation
    errors.json        -- inputs that must raise InvalidChordStringException

After running this script, update EXPECTED_CASE_COUNT in test_musicdsl_conformance.py
to the new total (printed at the end).
"""

import json
from pathlib import Path

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.serialize import serialize_chord

CASES_DIR = Path(__file__).resolve().parents[2] / "cases" / "chords"
CASES_DIR.mkdir(parents=True, exist_ok=True)


def _parse_case(name: str, input_str: str) -> dict:
    """Build a parse_chord case, blessing from the reference."""
    try:
        chord = Chord(input_str)
        model = serialize_chord(chord)
        return {
            "name": name,
            "op": "parse_chord",
            "args": {"input": input_str},
            "expect": {"model": {"chord": model}},
        }
    except InvalidChordStringException:
        return {
            "name": name,
            "op": "parse_chord",
            "args": {"input": input_str},
            "expect": {"error": True},
        }


def _encode_case(name: str, input_str: str) -> dict:
    """Build an encode_chord case, blessing from the reference."""
    try:
        chord = Chord(input_str)
        encoding = chord.encoding
        return {
            "name": name,
            "op": "encode_chord",
            "args": {"input": input_str},
            "expect": {"value": encoding},
        }
    except InvalidChordStringException:
        return {
            "name": name,
            "op": "encode_chord",
            "args": {"input": input_str},
            "expect": {"error": True},
        }


def _chord_cases(name: str, input_str: str) -> list[dict]:
    """Return both parse_chord and encode_chord cases for a single input."""
    return [
        _parse_case(f"{name}/parse", input_str),
        _encode_case(f"{name}/encode", input_str),
    ]


# ---------------------------------------------------------------------------
# BASIC: canonical chord forms across several roots
# ---------------------------------------------------------------------------
basic_inputs = [
    # (case_name, chord_string)
    ("basic/C-major-triad", "C"),
    ("basic/C-minor7", "C-7"),
    ("basic/C-major7", "C^7"),
    ("basic/C-diminished7", "Co7"),
    ("basic/C-half-dim7", "Ch7"),
    ("basic/C-augmented-triad", "C+"),
    ("basic/G-dominant7", "G7"),
    ("basic/D-minor7", "D-7"),
    ("basic/F-major", "F"),
    ("basic/Bb-major7", "Bb^7"),
    ("basic/Eb-dominant7", "Eb7"),
    ("basic/Ab-minor7", "Ab-7"),
    ("basic/A-major", "A"),
    ("basic/E-major", "E"),
    ("basic/B-major", "B"),
    ("basic/Gb-major7", "Gb^7"),
    ("basic/Db-minor7", "Db-7"),
]

basic_cases = []
for case_name, chord_str in basic_inputs:
    basic_cases.extend(_chord_cases(case_name, chord_str))

# ---------------------------------------------------------------------------
# SUS AMBIGUITY: C3 batch — adversarial for cross-port (Rust vs Python regex)
# ---------------------------------------------------------------------------
sus_inputs = [
    ("sus/Csus", "Csus"),
    ("sus/Csus4", "Csus4"),
    ("sus/Csus2", "Csus2"),
    ("sus/C4-shorthand", "C4"),
    ("sus/C9sus", "C9sus"),
    ("sus/C9sus4", "C9sus4"),
    ("sus/C7susb9", "C7susb9"),
    ("sus/C7b9sus", "C7b9sus"),
    ("sus/Csus7b9", "Csus7b9"),
    ("sus/Csus9", "Csus9"),
    ("sus/C-caret-shorthand", "C^"),
    ("sus/C7plus-aug5", "C7+"),
]

sus_cases = []
for case_name, chord_str in sus_inputs:
    sus_cases.extend(_chord_cases(case_name, chord_str))

# ---------------------------------------------------------------------------
# EXTENSIONS: add, 69, alt, multi-extension, aug5 folding
# ---------------------------------------------------------------------------
ext_inputs = [
    ("ext/C-major7-sharp11", "C^7#11"),
    ("ext/C-dominant13", "C13"),
    ("ext/C-dominant7-b9", "C7b9"),
    ("ext/C-dominant7-alt", "C7alt"),
    ("ext/C-add9", "Cadd9"),
    ("ext/C-69", "C69"),
    ("ext/C-diminished7-add9", "Co7add9"),
    ("ext/C-dominant7-b9-sharp11", "C7b9#11"),
    ("ext/C-minor7-b9", "C-7b9"),
    ("ext/C-dominant7-sharp9", "C7#9"),
    ("ext/C-dominant7-b9-sharp9", "C7b9#9"),
    ("ext/C-minor-major7", "C-^7"),
]

ext_cases = []
for case_name, chord_str in ext_inputs:
    ext_cases.extend(_chord_cases(case_name, chord_str))

# ---------------------------------------------------------------------------
# ENHARMONIC: flat/sharp root normalisation
# ---------------------------------------------------------------------------
enh_inputs = [
    ("enh/C-sharp-minor7-to-Db", "C#-7"),       # C# -> Db (flat normalised)
    ("enh/Db-major7", "Db^7"),
    ("enh/Cb-to-B", "Cb"),                        # Cb -> B (white-key enharmonic)
    ("enh/B-sharp-to-C", "B#"),                   # B# -> C
    ("enh/Fb-to-E", "Fb"),                        # Fb -> E
    ("enh/E-sharp-to-F", "E#"),                   # E# -> F
    ("enh/Ab-dominant7", "Ab7"),                  # Ab stays Ab (already flat)
    ("enh/Gb-major7", "Gb^7"),
    ("enh/Bb-minor7", "Bb-7"),
    ("enh/F-sharp-dominant7-to-Gb", "F#7"),       # F# -> Gb
    ("enh/G-sharp-minor7-to-Ab", "G#-7"),         # G# -> Ab
]

enh_cases = []
for case_name, chord_str in enh_inputs:
    enh_cases.extend(_chord_cases(case_name, chord_str))

# ---------------------------------------------------------------------------
# ERRORS: inputs that must raise InvalidChordStringException
# Only parse_chord error cases (encode_chord would raise the same errors).
# ---------------------------------------------------------------------------
error_inputs = [
    # (case_name, chord_string, description)
    ("err/xyzzy-no-root", "xyzzy", "garbage string — no [A-G] root"),
    ("err/VIII-numeral", "VIII", "Roman numeral — no [A-G] root"),
    ("err/pipe-two-chords", "C|D", "pipe separator — two chords"),
    # B#b9: B# normalises to C (len=1), triad=Major, 7th=_None, ext=b9 -> make_chord_attrs rejects
    ("err/B#b9-make_chord_attrs-rejection", "B#b9", "enharmonic natural root + leading-flat tension without seventh"),
    # Cadd² uses non-ASCII SUPERSCRIPT TWO — ASCII-digit contract rejects it
    ("err/Cadd-superscript2-non-ascii", "Cadd²", "non-ASCII superscript digit in extension"),
]

error_cases = []
for case_name, chord_str, _desc in error_inputs:
    # For errors we only write parse_chord (encode_chord would behave the same)
    case = _parse_case(case_name, chord_str)
    # Verify it's actually an error case (defensive: blessed oracle must agree)
    if "error" not in case["expect"]:
        raise AssertionError(
            f"BLESS FAILED: expected {chord_str!r} to raise but got: {case['expect']}"
        )
    error_cases.append(case)

# ---------------------------------------------------------------------------
# Write files
# ---------------------------------------------------------------------------
files = [
    ("basic.json", basic_cases),
    ("sus_ambiguity.json", sus_cases),
    ("extensions.json", ext_cases),
    ("enharmonic.json", enh_cases),
    ("errors.json", error_cases),
]

total = 0
for fname, cases in files:
    out = CASES_DIR / fname
    out.write_text(json.dumps(cases, indent=2) + "\n")
    total += len(cases)
    print(f"Wrote {len(cases):3d} cases -> {out}")

print(f"\nTotal chord cases: {total}")
print(f"Run: grep -r '\"op\"' conformance/music-dsl/cases | wc -l  to verify.")
