"""Deprecated: chord validation moved to tonalis.chords (MusicDSL-backed).
Kept as a shim so any `from tonalis.chord_grammar import is_valid_chord` still resolves.
"""
from tonalis.chords import is_valid_chord  # noqa: F401
