from __future__ import annotations
from functools import reduce

from typing import Union

from typing_extensions import Self

from music_dsl.encode import Encoding, EncodingMap

from .abstract_chord import AbstractChord, make_chord_attrs

from music_dsl.domain.static import (
    Extensions,
    Notes,
    ScaleDegree,
    Seventh,
    Triad,
)


class Chord(AbstractChord):
    __regex__ = r"^(?P<root>[A-G][b#]?)" + AbstractChord.__regex_suffix__

    def __init__(self, raw_chord):
        self._chord_attrs = self._parse_chord_string(raw_chord)
        self._chord_str = raw_chord
        self._root = self._chord_attrs.root
        self._encode()

    @property
    def root(self) -> Notes:
        return self._root

    @root.setter
    def root(self, note: Notes):
        self._root = note

    @property
    def encoding(self):
        return self.__encoding__.value

    @classmethod
    def from_attrs(
        cls,
        root: ScaleDegree,
        triad: Triad,
        _7th: Seventh,
        extensions: Extensions,
    ):
        _chord_attrs = make_chord_attrs(
            root,
            triad,
            _7th,
            extensions,
            cls._get_harmonic_function(root, triad, _7th),
        )
        key = super()._singleton_key(_chord_attrs)
        _new = cls._new(key)
        _new._chord_attrs = _chord_attrs
        return _new

    # White-key enharmonic spellings that the Notes enum does not carry directly.
    _ENHARMONIC_ROOTS = {"Cb": "B", "Fb": "E", "B#": "C", "E#": "F"}

    @classmethod
    def _parse_root(cls, match):
        match = cls._ENHARMONIC_ROOTS.get(match, match)
        return Notes(match).to_flat()

    def _encode(self):
        self.__encoding__ = Encoding(
            self.root, self.triad, self._7th, extensions=self.extensions
        )

    def __new__(cls: type[Self], chord_str: str) -> Self:
        key = hash(cls._parse_chord_string(chord_str))
        if key in cls.__instances__:
            return cls.__instances__[key]
        _new = object.__new__(cls)
        cls.__instances__[key] = _new
        return _new

    def __repr__(self) -> str:
        return f"<Chord {self._chord_str}>"
