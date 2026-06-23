"""Canonical serializer for the music_dsl Python reference.

``serialize_chord`` is the cross-port contract: it defines the exact JSON
shape that all ports (TS, Rust) must reproduce for `parse_chord` ops.  This
is an ADDITIVE module — it imports from the domain but does NOT modify any
domain class (Chord, AbstractChord, ChordAttrs, encoding, singleton, etc.).

Shape (frozen by the schema + blessed cases)::

    {
      "root":               <Notes .value, flat-normalised: "C", "Db", ...>,
      "triad":              <Triad .value: "" major, "-" minor, "h","o","+","sus","sus2","sus4">,
      "seventh":            <Seventh .value: "^7", "7", "">,
      "extensions":         [<Extensions .value in parse order: "#11", "b9", ...>],
      "harmonic_function":  <HarmonicFunctions NAME: "Tonic"|"Dominant"|"Subdominant">,
      "substitution":       <bool>
    }

No ``bass`` field (the parser discards bass), no ``encoding`` field (asserted
separately via the ``encode_chord`` op).

``serialize_numeric_chord`` has the same field set EXCEPT ``root`` is a
ScaleDegree value (Roman numeral string like ``"ii"``, ``"V"``, ``"bVI"``)
rather than a Notes value. Shape::

    {
      "numerator":   <chord-model with ScaleDegree-valued root>,
      "denominator": <chord-model with ScaleDegree-valued root> | null
    }
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music_dsl.domain.chords.chord import Chord
    from music_dsl.domain.chords.abstract_chord import ChordAttrs
    from music_dsl.domain.chords.numeric_chord import NumericChord


def serialize_chord(chord: "Chord") -> dict:
    """Return the canonical dict representation of *chord*.

    The dict is fully JSON-serialisable (all values are str/bool/list of str).
    The caller owns JSON serialisation; this function only builds the dict.

    Args:
        chord: A ``music_dsl.domain.chords.chord.Chord`` instance.

    Returns:
        dict with keys: root, triad, seventh, extensions, harmonic_function,
        substitution.
    """
    attrs = chord._chord_attrs
    return {
        "root": chord.root.value,
        "triad": attrs.triad.value,
        "seventh": attrs._7th.value,
        "extensions": [ext.value for ext in attrs.extensions],
        "harmonic_function": attrs.harmonic_function.name,
        "substitution": attrs.substitution,
    }


def _serialize_chord_attrs(attrs: "ChordAttrs") -> dict:
    """Serialize a ChordAttrs to the canonical chord-model dict.

    Used by ``serialize_numeric_chord`` where attrs.root is a ScaleDegree rather
    than a Notes. The field set is identical to ``serialize_chord``'s output —
    only the ``root`` type differs (ScaleDegree .value vs Notes .value).

    Args:
        attrs: A ``ChordAttrs`` instance whose root is a ScaleDegree.

    Returns:
        dict with keys: root, triad, seventh, extensions, harmonic_function,
        substitution. All values are str/bool/list of str (JSON-serialisable).
    """
    return {
        "root": attrs.root.value,
        "triad": attrs.triad.value,
        "seventh": attrs._7th.value,
        "extensions": [ext.value for ext in attrs.extensions],
        "harmonic_function": attrs.harmonic_function.name,
        "substitution": attrs.substitution,
    }


def serialize_numeric_chord(numeric: "NumericChord") -> dict:
    """Return the canonical dict representation of a NumericChord.

    Shape::

        {
          "numerator":   { "root": <ScaleDegree value e.g. "ii","V","bVI">,
                           "triad": ..., "seventh": ..., "extensions": [...],
                           "harmonic_function": ..., "substitution": bool },
          "denominator": <same shape> | null
        }

    The field set is identical to ``serialize_chord``'s chord-model EXCEPT
    ``root`` is a ScaleDegree value (Roman numeral string). No ``bass`` or
    ``encoding`` field.

    Args:
        numeric: A ``NumericChord`` instance.

    Returns:
        dict with keys: numerator (chord-model dict), denominator (chord-model
        dict or null). Fully JSON-serialisable.
    """
    numerator_model = _serialize_chord_attrs(numeric._chord_attrs)
    denominator_model = (
        _serialize_chord_attrs(numeric.denominator._chord_attrs)
        if numeric.denominator
        else None
    )
    return {
        "numerator": numerator_model,
        "denominator": denominator_model,
    }
