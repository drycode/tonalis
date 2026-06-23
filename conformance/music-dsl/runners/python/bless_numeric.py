"""One-shot: generate and BLESS conformance/music-dsl/cases/{numeric,transactions}/*.json
from the frozen Python reference.

Run from the tonalis root:
    source .venv/bin/activate
    python conformance/music-dsl/runners/python/bless_numeric.py

Files produced:
    cases/numeric/parse.json          -- numeric parse cases
    cases/numeric/slash.json          -- slash chord numeric cases
    cases/numeric/substitution.json   -- substitution branch anchors
    cases/numeric/errors.json         -- error sentinels
    cases/transactions/modulate.json  -- modulate(semitones, note/degree)
    cases/transactions/is_diatonic.json    -- is_diatonic × 3 scales × roots
    cases/transactions/hf_in_key.json     -- harmonic_function_in_key cases
    cases/transactions/chord_in_key.json  -- chord_in_key realization cases

After running, update EXPECTED_CASE_COUNT in test_musicdsl_conformance.py.
"""

import json
from pathlib import Path

from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.chords.numeric_chord import NumericChord, IncorrectHarmonicFunctionException
from music_dsl.domain.chords.abstract_chord import InvalidChordStringException
from music_dsl.domain.static import Notes, ScaleDegree
from music_dsl.encode import Scales
from music_dsl.transactions import modulate, is_diatonic, harmonic_function_in_key, chord_in_key
from music_dsl.serialize import serialize_chord, serialize_numeric_chord, _serialize_chord_attrs

CASES_DIR = Path(__file__).resolve().parents[2] / "cases"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _numeric_case(name: str, input_str: str) -> dict:
    """Build a parse_numeric case, blessing from the reference."""
    try:
        nc = NumericChord.from_chord_string(input_str)
        model = serialize_numeric_chord(nc)
        return {
            "name": name,
            "op": "parse_numeric",
            "args": {"input": input_str},
            "expect": {"model": {"numeric": model}},
        }
    except (InvalidChordStringException, Exception):
        return {
            "name": name,
            "op": "parse_numeric",
            "args": {"input": input_str},
            "expect": {"error": True},
        }


def _numeric_from_chord_case(name: str, key_root: str, chord: str, substitution: bool) -> dict:
    """Build a numeric_from_chord case, blessing from the reference."""
    try:
        attrs = NumericChord._from_chord(Notes(key_root), Chord(chord), substitution)
        model = _serialize_chord_attrs(attrs)
        return {
            "name": name,
            "op": "numeric_from_chord",
            "args": {"key_root": key_root, "chord": chord, "substitution": substitution},
            "expect": {"model": {"numeric": model}},
        }
    except (IncorrectHarmonicFunctionException, InvalidChordStringException):
        return {
            "name": name,
            "op": "numeric_from_chord",
            "args": {"key_root": key_root, "chord": chord, "substitution": substitution},
            "expect": {"error": True},
        }


def _modulate_case(name: str, semitones: int, note: str) -> dict:
    """Build a modulate case."""
    try:
        n = ScaleDegree(note)
    except ValueError:
        n = Notes(note)
    result = modulate(semitones, n).value
    return {
        "name": name,
        "op": "modulate",
        "args": {"semitones": semitones, "note": note},
        "expect": {"value": result},
    }


def _is_diatonic_case(name: str, root: str, scale: str, chord: str) -> dict:
    """Build an is_diatonic case."""
    result = is_diatonic(Notes(root), Scales[scale], Chord(chord))
    return {
        "name": name,
        "op": "is_diatonic",
        "args": {"root": root, "scale": scale, "chord": chord},
        "expect": {"value": result},
    }


def _hf_in_key_case(name: str, key_root: str, key_is_minor: bool, chord: str) -> dict:
    """Build a harmonic_function_in_key case."""
    result = harmonic_function_in_key(Notes(key_root), key_is_minor, Chord(chord)).name
    return {
        "name": name,
        "op": "harmonic_function_in_key",
        "args": {"key_root": key_root, "key_is_minor": key_is_minor, "chord": chord},
        "expect": {"value": result},
    }


def _chord_in_key_case(name: str, numeric: str, key_root: str) -> dict:
    """Build a chord_in_key case."""
    nc = NumericChord.from_chord_string(numeric)
    realized = chord_in_key(nc, Notes(key_root))
    model = serialize_chord(realized)
    return {
        "name": name,
        "op": "chord_in_key",
        "args": {"numeric": numeric, "key_root": key_root},
        "expect": {"model": {"chord": model}},
    }


# ---------------------------------------------------------------------------
# NUMERIC / PARSE
# ---------------------------------------------------------------------------
parse_inputs = [
    ("numeric/parse/ii-7", "ii-7"),
    ("numeric/parse/V7", "V7"),
    ("numeric/parse/I^7", "I^7"),
    ("numeric/parse/bVI^7", "bVI^7"),
    ("numeric/parse/sharp-ivo7", "#ivo7"),
    ("numeric/parse/sV7", "sV7"),
]

parse_cases = [_numeric_case(name, input_str) for name, input_str in parse_inputs]

# ---------------------------------------------------------------------------
# NUMERIC / SLASH
# ---------------------------------------------------------------------------
slash_inputs = [
    ("numeric/slash/V7-slash-V", "V7/V"),
    ("numeric/slash/ii-7-slash-IV", "ii-7/IV"),
]

slash_cases = [_numeric_case(name, input_str) for name, input_str in slash_inputs]

# ---------------------------------------------------------------------------
# NUMERIC / SUBSTITUTION ANCHORS
# (bless from reference — do NOT hand-invent)
# ---------------------------------------------------------------------------
# Branch (c): A==8 (m6 ascending) fires for E-7 in C (E->C = 8)
# Branch (c): A==4 (M3-up inversion) does NOT fire for Ab-7 in C (Ab->C = 4)
# Branch (b): Db7 in C — Db is Dominant, branch (b) fires (modulate Tritone -> V)
substitution_cases = [
    # E-7 in C, sub=False: root=iii (no substitution logic)
    _numeric_from_chord_case("substitution/E-m7-in-C-no-sub", "C", "E-7", False),
    # E-7 in C, sub=True: branch (c) fires (A==8), root changes from iii -> #vi
    _numeric_from_chord_case("substitution/E-m7-in-C-with-sub", "C", "E-7", True),
    # Ab-7 in C, sub=False: root=bvi
    _numeric_from_chord_case("substitution/Ab-m7-in-C-no-sub", "C", "Ab-7", False),
    # Ab-7 in C, sub=True: branch (c) does NOT fire (A==4, M3-up inversion), root stays bvi
    _numeric_from_chord_case("substitution/Ab-m7-in-C-with-sub", "C", "Ab-7", True),
    # Db7 in C, sub=True: tritone sub — branch (b) fires (Dominant), root -> V
    _numeric_from_chord_case("substitution/Db7-in-C-with-sub", "C", "Db7", True),
]

# Cross-check: E-7 sub=True should DIFFER from sub=False
_e_no_sub = next(c for c in substitution_cases if c["name"] == "substitution/E-m7-in-C-no-sub")
_e_with_sub = next(c for c in substitution_cases if c["name"] == "substitution/E-m7-in-C-with-sub")
assert _e_no_sub["expect"].get("model", {}).get("numeric", {}).get("root") != \
       _e_with_sub["expect"].get("model", {}).get("numeric", {}).get("root"), \
    f"BLESS FAILED: E-7 sub=True root should differ from sub=False, but both got the same root"

# Cross-check: Ab-7 sub=True should EQUAL sub=False (branch-c must NOT fire for A==4)
_ab_no_sub = next(c for c in substitution_cases if c["name"] == "substitution/Ab-m7-in-C-no-sub")
_ab_with_sub = next(c for c in substitution_cases if c["name"] == "substitution/Ab-m7-in-C-with-sub")
assert _ab_no_sub["expect"].get("model", {}).get("numeric", {}).get("root") == \
       _ab_with_sub["expect"].get("model", {}).get("numeric", {}).get("root"), \
    f"BLESS FAILED: Ab-7 sub=True root should equal sub=False (branch-c must not fire for A==4)"

print("Substitution anchor cross-checks PASSED.")

# ---------------------------------------------------------------------------
# NUMERIC / ERRORS
# ---------------------------------------------------------------------------
# IncorrectHarmonicFunctionException: chord whose harmonic function doesn't match
# the substitution branch's requirement. Branch (a) requires Subdominant;
# a Dominant-function chord at Tritone distance fires (a) and then raises.
# Actually branch (a) is: semitones(chord.root->key_root)==Tritone AND chord.hf != Subdominant
# Example: C7 in F# (F#->C ascending = 6 = Tritone; C7 is Dominant, not Subdominant) -> raises
error_cases = [
    # IncorrectHarmonicFunctionException: C7 at tritone from key F# is Dominant, not Subdominant
    _numeric_from_chord_case("numeric/errors/incorrect-hf-tritone-not-subdominant", "F#", "C7", True),
    # InvalidChordStringException: empty numerator
    _numeric_case("numeric/errors/empty-numerator", ""),
]

# Verify they are indeed errors
for ec in error_cases:
    assert "error" in ec["expect"], f"BLESS FAILED: {ec['name']} expected error but got: {ec['expect']}"

# ---------------------------------------------------------------------------
# TRANSACTIONS / MODULATE
# ---------------------------------------------------------------------------
modulate_cases = [
    # Notes path: C + perfect fifth up (7) = G
    _modulate_case("transactions/modulate/C-up-P5", 7, "C"),
    # Notes path: D + minor third up (3) = F
    _modulate_case("transactions/modulate/D-up-m3", 3, "D"),
    # Notes path: Ab + major second up (2) = Bb
    _modulate_case("transactions/modulate/Ab-up-M2", 2, "Ab"),
    # ScaleDegree path: bVII + perfect fifth (7) = bIII (preserves flat)
    _modulate_case("transactions/modulate/bVII-up-P5", 7, "bVII"),
    # ScaleDegree path: ii (minor) + major second (2) = iii (preserves minor)
    _modulate_case("transactions/modulate/ii-minor-up-M2", 2, "ii"),
    # ScaleDegree path: V + tritone (6) = bII
    _modulate_case("transactions/modulate/V-up-Tritone", 6, "V"),
]

# ---------------------------------------------------------------------------
# TRANSACTIONS / IS_DIATONIC
# ---------------------------------------------------------------------------
# Diatonic + non-diatonic for Major, Minor, HarmonicMinor
is_diatonic_cases = [
    # Major scale
    _is_diatonic_case("transactions/is_diatonic/C-major-C^7-diatonic", "C", "Major", "C^7"),
    _is_diatonic_case("transactions/is_diatonic/C-major-D-7-diatonic", "C", "Major", "D-7"),
    _is_diatonic_case("transactions/is_diatonic/C-major-G7-diatonic", "C", "Major", "G7"),
    _is_diatonic_case("transactions/is_diatonic/C-major-Db^7-non-diatonic", "C", "Major", "Db^7"),
    _is_diatonic_case("transactions/is_diatonic/C-major-Ab7-non-diatonic", "C", "Major", "Ab7"),
    # Minor scale (natural minor)
    _is_diatonic_case("transactions/is_diatonic/C-minor-C-7-diatonic", "C", "Minor", "C-7"),
    _is_diatonic_case("transactions/is_diatonic/C-minor-Eb^7-diatonic", "C", "Minor", "Eb^7"),
    _is_diatonic_case("transactions/is_diatonic/C-minor-Bb7-diatonic", "C", "Minor", "Bb7"),
    _is_diatonic_case("transactions/is_diatonic/C-minor-E^7-non-diatonic", "C", "Minor", "E^7"),
    _is_diatonic_case("transactions/is_diatonic/C-minor-A^7-non-diatonic", "C", "Minor", "A^7"),
    # HarmonicMinor scale
    _is_diatonic_case("transactions/is_diatonic/C-harm-minor-C-^7-diatonic", "C", "HarmonicMinor", "C-^7"),
    _is_diatonic_case("transactions/is_diatonic/C-harm-minor-G7-diatonic", "C", "HarmonicMinor", "G7"),
    _is_diatonic_case("transactions/is_diatonic/C-harm-minor-Bb^7-non-diatonic", "C", "HarmonicMinor", "Bb^7"),
    _is_diatonic_case("transactions/is_diatonic/G-major-D7-diatonic", "G", "Major", "D7"),
    _is_diatonic_case("transactions/is_diatonic/G-major-Db7-non-diatonic", "G", "Major", "Db7"),
]

# ---------------------------------------------------------------------------
# TRANSACTIONS / HF_IN_KEY
# ---------------------------------------------------------------------------
hf_in_key_cases = [
    # Minor tonic: i-7 in a minor key = Tonic (key-dependent override)
    _hf_in_key_case("transactions/hf_in_key/C-minor-tonic-C-7", "C", True, "C-7"),
    # Major tonic: I^7 in major = Tonic (quality-based, unchanged)
    _hf_in_key_case("transactions/hf_in_key/C-major-tonic-C^7", "C", False, "C^7"),
    # Major dominant: G7 in C = Dominant
    _hf_in_key_case("transactions/hf_in_key/C-major-dominant-G7", "C", False, "G7"),
    # Blues I7: C7 in C major stays Dominant (not overridden to Tonic)
    _hf_in_key_case("transactions/hf_in_key/C-major-blues-I7", "C", False, "C7"),
    # Subdominant: D-7 in C major = Subdominant (quality-based)
    _hf_in_key_case("transactions/hf_in_key/C-major-subdominant-D-7", "C", False, "D-7"),
    # Different root: ii-7 in G = Subdominant
    _hf_in_key_case("transactions/hf_in_key/G-major-subdominant-A-7", "G", False, "A-7"),
]

# ---------------------------------------------------------------------------
# TRANSACTIONS / CHORD_IN_KEY
# ---------------------------------------------------------------------------
chord_in_key_cases = [
    # V7 in C = G7
    _chord_in_key_case("transactions/chord_in_key/V7-in-C", "V7", "C"),
    # V7/V in C = D7
    _chord_in_key_case("transactions/chord_in_key/V7-slash-V-in-C", "V7/V", "C"),
    # ii-7 in C = D-7
    _chord_in_key_case("transactions/chord_in_key/ii-7-in-C", "ii-7", "C"),
    # I^7 in C = C^7
    _chord_in_key_case("transactions/chord_in_key/I^7-in-C", "I^7", "C"),
    # V7 in G = D7
    _chord_in_key_case("transactions/chord_in_key/V7-in-G", "V7", "G"),
    # bVI^7 in C = Ab^7
    _chord_in_key_case("transactions/chord_in_key/bVI^7-in-C", "bVI^7", "C"),
]

# ---------------------------------------------------------------------------
# Write files
# ---------------------------------------------------------------------------
numeric_dir = CASES_DIR / "numeric"
numeric_dir.mkdir(parents=True, exist_ok=True)

transactions_dir = CASES_DIR / "transactions"
transactions_dir.mkdir(parents=True, exist_ok=True)

files = [
    (numeric_dir / "parse.json", parse_cases),
    (numeric_dir / "slash.json", slash_cases),
    (numeric_dir / "substitution.json", substitution_cases),
    (numeric_dir / "errors.json", error_cases),
    (transactions_dir / "modulate.json", modulate_cases),
    (transactions_dir / "is_diatonic.json", is_diatonic_cases),
    (transactions_dir / "hf_in_key.json", hf_in_key_cases),
    (transactions_dir / "chord_in_key.json", chord_in_key_cases),
]

total = 0
for path, cases in files:
    path.write_text(json.dumps(cases, indent=2) + "\n")
    total += len(cases)
    print(f"Wrote {len(cases):3d} cases -> {path}")

print(f"\nTotal new cases: {total}")
print(f"(Previous total was 216; new total = 216 + {total} = {216 + total})")
