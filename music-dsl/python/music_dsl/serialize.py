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
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music_dsl.domain.chords.chord import Chord


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
