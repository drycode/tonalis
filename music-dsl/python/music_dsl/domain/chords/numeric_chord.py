from __future__ import annotations

from functools import cache
from typing import Union
from typing_extensions import Self, TypeAlias


from music_dsl.domain.static import Intervals, HarmonicFunctions
from music_dsl.helpers import semitones_apart_ascending, m_or_M_scaledegree
from music_dsl.transactions import modulate

from .abstract_chord import (
    AbstractChord,
    ChordAttrs,
    InvalidChordStringException,
    make_chord_attrs,
)
from .chord import Chord

from music_dsl.domain.static import (
    SCALE_DEGREES,
    Notes,
    ScaleDegree,
    Triad,
    Seventh,
    Extensions,
)


class IncorrectHarmonicFunctionException(Exception):
    def __init__(self, chord, diatonic_key_root, harmonic_function) -> None:
        self.message = (
            f"{chord} in the key of {diatonic_key_root} is not {harmonic_function}"
        )
        super().__init__(self.message)


class NumericChord(AbstractChord):
    __regex__ = r"^(?P<root>[b#]?[ivVI]{1,4})" + AbstractChord.__regex_suffix__

    def __init__(
        self,
        diatonic_key_root: Notes,
        numerator: Chord,
        denominator: AbstractChord = None,
        substitution=False,
    ):
        denominator = self.make_denominator(diatonic_key_root, denominator)
        self._chord_attrs = self._from_chord(
            diatonic_key_root if not denominator else denominator.root,
            numerator,
            substitution,
        )

        self._denominator: NumericChord = denominator

    def make_denominator(self, diatonic_key_root, denominator):
        if (
            denominator
            and denominator is not self
            and denominator.root != diatonic_key_root
        ):
            if isinstance(denominator, Chord):
                denominator = NumericChord.from_attrs(
                    self._from_chord(diatonic_key_root, denominator)
                )
            return denominator

    @property
    def root(self) -> ScaleDegree:
        return self._chord_attrs.root

    @property
    def denominator(self) -> NumericChord:
        return self._denominator if hasattr(self, "_denominator") else None

    @property
    def is_substitution(self):
        return self._chord_attrs.substitution

    @classmethod
    def from_chord_string(cls, chord_str: str):
        numerator, denominator = NumericChord._get_numerator_denominator(chord_str)
        return cls._make_new(numerator, denominator)

    def to_json(self):
        return {
            "numerator": self._chord_attrs,
            "denominator": self.denominator._chord_attrs if self.denominator else None,
        }

    @staticmethod
    def _get_numerator_denominator(chord_str: str):
        _split = chord_str.split("/")
        numerator, denominator = _split[0], None
        if len(_split) == 2:
            denominator = _split[1]
        return numerator, denominator

    @classmethod
    def _make_new(cls, numerator_str, denominator_str):
        if not numerator_str:
            raise InvalidChordStringException(
                "Attempted to parse a numeric chord with an empty numerator"
            )
        num_substitution = False
        if numerator_str[0] == "s":
            num_substitution = True
            numerator_str = numerator_str[1:]

        _chord_attrs = cls._parse_chord_string(
            numerator_str, substitution=num_substitution
        )

        if denominator_str:
            _den = cls.from_chord_string(denominator_str)
            key = super()._singleton_key(_chord_attrs, _den._chord_attrs)
            _new = cls._new(key)
            _new._denominator = _den
        else:
            key = super()._singleton_key(_chord_attrs)
            _new = cls._new(key)
        _new._chord_attrs = _chord_attrs
        return _new

    @classmethod
    def from_attrs(cls, chord_attrs: ChordAttrs, denominator: ChordAttrs = None):
        key = super()._singleton_key(chord_attrs, denominator)
        _new = cls._new(key)
        _new._chord_attrs = chord_attrs
        return _new

    @staticmethod
    @cache
    def _find_scale_degree(
        root: Notes, note: Notes, triad: Triad = None
    ) -> ScaleDegree:
        scale_degree = SCALE_DEGREES[semitones_apart_ascending(root, note)]
        # Passing/auxiliary diminished chords are conventionally spelled with a
        # sharp on a chromatic degree (they ascend by half-step): #io7, #ivo7 --
        # not the flat default (bIIo7, bVo7) that SCALE_DEGREES carries.
        if triad == Triad.Diminished and scale_degree.is_flat:
            scale_degree = scale_degree.to_sharp()
        return m_or_M_scaledegree(scale_degree, triad)

    @classmethod
    def _parse_root(cls, match):
        return ScaleDegree(match)

    @classmethod
    def _from_chord(
        cls, diatonic_key_root: Notes, chord: AbstractChord, substitution=False
    ) -> ChordAttrs:
        scale_degree = NumericChord._find_scale_degree(
            diatonic_key_root, chord.root, chord.triad
        )
        if substitution:
            if (
                Intervals(semitones_apart_ascending(chord.root, diatonic_key_root))
                == Intervals.Tritone
            ):
                ### Subdominant variations like Db-7 Ab7 G
                if chord.harmonic_function != HarmonicFunctions.Subdominant:
                    raise IncorrectHarmonicFunctionException(
                        chord, diatonic_key_root, HarmonicFunctions.Subdominant
                    )
                scale_degree = modulate(
                    Intervals.Tritone.value + Intervals.M2.value, scale_degree
                )
            elif chord.harmonic_function == HarmonicFunctions.Dominant:
                # Dominant variations
                scale_degree = modulate(
                    Intervals.Tritone.value,
                    scale_degree,
                )
            # A = ascending(chord.root -> key root) mod 12. A==8 IS the "m6 up / M3 down"
            # root motion (both collapse to 8 here); structural == matches only that, not
            # the M3-up inversion (A==4).
            elif (
                Intervals(semitones_apart_ascending(chord.root, diatonic_key_root))
                == Intervals.m6
            ):
                ### Subdominant variations like Db-7 D7 G
                scale_degree = modulate(
                    Intervals.m6.down() + Intervals.M2.value, scale_degree
                )

        return make_chord_attrs(
            scale_degree,
            chord.triad,
            chord._7th,
            chord.extensions,
            cls._get_harmonic_function(scale_degree, chord.triad, chord._7th),
            substitution,
        )

    def __new__(
        cls: TypeAlias[Self],
        tonic: Notes,
        numerator: Chord,
        denominator: Chord = None,
        substitution=False,
    ) -> TypeAlias[Self]:
        chord_attrs = cls._from_chord(tonic, numerator, substitution=substitution)
        den_chord_attrs = (
            cls._from_chord(tonic, denominator, substitution=substitution)
            if denominator
            else None
        )
        key = super()._singleton_key(chord_attrs, resolves_to=den_chord_attrs)
        _new = cls._new(key)
        _new._denominator = cls._new(super()._singleton_key(chord_attrs))
        return _new

    def __hash__(self) -> int:
        return self._singleton_key(
            self._chord_attrs,
            self.denominator._chord_attrs if self.denominator else None,
        )

    def __repr__(self):
        numerator = repr(self._chord_attrs)
        if (
            hasattr(self, "_denominator")
            and self.denominator
            and self.denominator._chord_attrs.root.to_major() != ScaleDegree.I
        ):
            denominator = "/" + repr(self.denominator) if self.denominator else ""
            return numerator + denominator

        return numerator

    def __eq__(self, __o: object) -> bool:
        if (
            self.denominator
            and self.denominator.root.to_major() != ScaleDegree.I
            and __o.denominator
        ):
            return super().__eq__(__o) and self.denominator.root == __o.denominator.root
        return super().__eq__(__o)

    def in_key(self, key_root):
        """Realize this numeral into an absolute Chord in the given key.
        Thin delegator to transactions.chord_in_key (local import: the
        transactions module imports from this one)."""
        from music_dsl.transactions import chord_in_key
        return chord_in_key(self, key_root)


def build_numeric_chord(
    root: ScaleDegree, triad: Triad, _7th: Seventh, extensions: Extensions
):
    return NumericChord.from_attrs(
        ChordAttrs(
            root,
            triad,
            _7th,
            extensions,
            Chord._get_harmonic_function(root, triad, _7th),
        )
    )
