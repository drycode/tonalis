from __future__ import annotations
from dataclasses import dataclass

import re
from abc import abstractclassmethod
from functools import cache, reduce
from typing import List, Tuple, Union
from music_dsl.helpers import m_or_M_scaledegree, validate_attr_inputs
import logging

logger = logging.getLogger(__name__)


EMPTY_CHORD_ENCODING = int("1000000000000000000", 2)

from music_dsl.domain.static import (
    Extensions,
    HarmonicFunctions,
    Notes,
    ScaleDegree,
    Seventh,
    Triad,
)


_ROOT_IDX = 1
_TRIAD_IDX = 4
_7TH_IDX = 6
_SUS_IDX = 9
_EXT_IDX = 10


@dataclass
class ChordAttrs:
    root: Union[ScaleDegree, Notes]
    triad: Triad
    _7th: Seventh
    extensions: Tuple[Extensions]
    harmonic_function: HarmonicFunctions
    substitution: bool = False

    def to_json(self):
        return self.__dict__

    def __hash__(self):
        return hash(tuple(self.__dict__.values()))

    def __repr__(self):
        sev_triad = (self.triad, self._7th)
        if self.triad in {Triad.Sus, Triad.Sus2, Triad.Sus4}:
            sev_triad = (self._7th, self.triad)
        return reduce(
            lambda x, y: x + str(y.value),
            self.extensions,
            reduce(
                lambda x, y: str(x) + str(y.value) if y else str(x),
                sev_triad,
                f"{self.root.value}",
            ),
        )


def make_chord_attrs(
    root, triad, _7th, extensions, harmonic_function=None, substitution=False
):
    validate_attr_inputs(
        _7th,
        extensions,
    )
    if isinstance(root, ScaleDegree):
        root = m_or_M_scaledegree(root, triad)

    return ChordAttrs(root, triad, _7th, extensions, harmonic_function, substitution)


class InvalidChordStringException(Exception):
    ...


class AbstractChord:
    __regex__ = ...
    __regex_suffix__ = (
        r"((sus|sus4|sus2|[ho\-])?)(([\^7]{1,2})?)((sus|sus4|sus2)?([b95136#]{1,})?)$"
    )
    __instances__ = dict()

    def __init__(self):
        self._chord_attrs

    @property
    def root(self):
        return self._chord_attrs.root

    @property
    def triad(self):
        return self._chord_attrs.triad

    @property
    def _7th(self):
        return self._chord_attrs._7th

    @property
    def extensions(self):
        return self._chord_attrs.extensions

    @property
    def harmonic_function(self):
        return self._chord_attrs.harmonic_function

    def to_json(self):
        return self._chord_attrs

    @classmethod
    def _get_extensions(cls, ext_string: str) -> Tuple[Extensions, ...]:
        extensions_regex = r"([b#]?[\d]{1,2})"
        matches = []
        while ext_string:
            result = re.match(extensions_regex, ext_string)
            start, end = result.regs[0]
            matches.append(Extensions(ext_string[start:end]))
            ext_string = ext_string[end:]

        return tuple(matches)

    @classmethod
    @cache
    def _parse_chord_string(cls, raw_chord, substitution=False) -> ChordAttrs:
        if "/" in raw_chord:
            logger.info("Doesn't currently support slash chords.")
            raw_chord = raw_chord.split("/")[0]
        match_groups = re.match(cls.__regex__, raw_chord)
        AbstractChord._verify_chord_string(raw_chord, match_groups)
        _root = cls._parse_root(match_groups[_ROOT_IDX])
        _sus = match_groups[_SUS_IDX]
        if _sus and match_groups[_TRIAD_IDX]:
            raise Exception(
                "Shouldn't be able to have a Triad and a Sus defined at the same time."
            )
        _triad = Triad(_sus) if _sus else Triad(match_groups[_TRIAD_IDX])
        _7th = Seventh(match_groups[_7TH_IDX])
        _extensions = cls._get_extensions(match_groups[_EXT_IDX])
        _harmonic_function = cls._get_harmonic_function(_root, _triad, _7th)
        return make_chord_attrs(
            _root, _triad, _7th, _extensions, _harmonic_function, substitution
        )

    @staticmethod
    def _verify_chord_string(raw_chord, match_groups):
        if "|" in raw_chord:
            raise InvalidChordStringException(
                "There's more than one chord in this attempt to parse"
            )

        if not match_groups:
            raise InvalidChordStringException(
                f'Attempted to parse "{raw_chord}" which is invalid'
            )

    @abstractclassmethod
    def _parse_root(cls, match):
        ...

    @staticmethod
    def _get_harmonic_function(
        _root: Union[Notes, ScaleDegree], _triad: Triad, _7th: Seventh
    ) -> HarmonicFunctions:
        return {
            (Triad.Minor, Seventh.Minor): HarmonicFunctions.Subdominant,
            (Triad.HalfDiminished, Seventh.Minor): HarmonicFunctions.Subdominant,
            (Triad.Major, Seventh.Minor): HarmonicFunctions.Dominant,
            (Triad.Major, Seventh.Major): HarmonicFunctions.Tonic,
            (Triad.Minor, Seventh.Major): HarmonicFunctions.Tonic,
        }.get((_triad, _7th), HarmonicFunctions.Tonic)

    @staticmethod
    def _singleton_key(chord_attrs: ChordAttrs, resolves_to: ChordAttrs = None):
        return (
            hash(repr(chord_attrs) + repr(resolves_to))
            if resolves_to
            else hash(repr(chord_attrs))
        )

    @classmethod
    def _new(cls, key):
        if key in cls.__instances__:
            return cls.__instances__[key]
        _new = object.__new__(cls)
        cls.__instances__[key] = _new
        return _new

    def __hash__(self) -> int:
        return hash(repr(self._chord_attrs))

    def __eq__(self, __o: object) -> bool:
        return (
            self.root.to_flat() == __o.root.to_flat()
            and self.harmonic_function == __o.harmonic_function
            and self.triad == __o.triad
            and self._7th == __o._7th
        )
