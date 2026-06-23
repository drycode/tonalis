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

# Chord suffix is parsed with named groups (see ``__regex_suffix__``):
#   triad   - triad quality token (-, h, o, +, sus...)
#   seventh - 7th token (^7, ^, 7)
#   alt     - literal "alt" (altered dominant)
#   ext     - run of extension tokens (b9, #11, 13, add9, 6, 9 ...)
#   sus2    - a sus token appearing AFTER the 7th/extensions (e.g. 9sus, 7b9sus)
# Subclasses contribute a leading named ``root`` group.


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
        # A tritone substitution carries an "s" prefix (sV7/V) so the repr
        # round-trips through from_chord_string and stays distinct from the plain
        # dominant it sits a tritone from. Absolute Chords never set this flag.
        prefix = "s" if self.substitution else ""
        return prefix + reduce(
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

    # Reject the notationally-unspellable "natural root + leading flat/sharp tension,
    # no seventh, bare major triad" combination. In the chord-string grammar a
    # flat/sharp directly after a natural letter binds to the ROOT (`Cb9` parses as
    # Cb+9, not C+b9), and a bare major triad emits no quality token to separate the
    # root from the tension. So a chord like a C-major triad carrying a b9 (only
    # reachable via an enharmonic-normalizing root such as B#->C) has no
    # round-trippable repr: `repr` would emit `Cb9`, which re-parses as Cb+9 -> B add9.
    # Such altered tensions also require a seventh to be musically well-formed. A
    # non-major triad ("-"/"h"/"o"/"+") or a seventh provides a separator, so those
    # are unaffected; a root that already carries an accidental (Db, F#) cannot collide.
    if (
        isinstance(root, Notes)
        and triad is Triad.Major
        and _7th is Seventh._None
        and len(root.value) == 1
        and extensions
        and extensions[0].value[:1] in ("b", "#")
    ):
        raise InvalidChordStringException(
            f"{root.value}{extensions[0].value}: an altered tension with no seventh "
            "binds its accidental to the root and has no spellable canonical form"
        )

    return ChordAttrs(root, triad, _7th, extensions, harmonic_function, substitution)


class InvalidChordStringException(Exception): ...


class AbstractChord:
    __regex__ = ...
    # sus can appear in three places across iReal/legacy notations:
    #   * before the 7th, as a triad  (Csus, Gsus4)
    #   * after the 7th, canonical    (Bb7sus#9)
    #   * after the extensions        (F9sus, G7b9sus)
    # Each is captured separately and consolidated in _parse_chord_string.
    __regex_suffix__ = (
        r"(?P<triad>sus4|sus2|sus|[ho+\-])?"
        r"(?P<seventh>\^7|\^|7)?"
        r"(?P<alt>alt)?"
        r"(?P<sus1>sus4|sus2|sus)?"
        r"(?P<ext>(?:add|[b#]?\d{1,2})*?)"
        r"(?P<sus2>sus4|sus2|sus)?"
        r"$"
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
        if not ext_string:
            return tuple()
        # iReal writes "add9" for an added 9th and "69" as a compound 6/9 token;
        # normalise both before tokenising into individual extensions.
        ext_string = ext_string.replace("add", "")
        ext_string = ext_string.replace("69", "6,9")

        extensions_regex = r"([b#]?[\d]{1,2})"
        matches = []
        pos = 0
        while pos < len(ext_string):
            result = re.match(extensions_regex, ext_string[pos:])
            if result is None:
                # Skip a separator (or any unexpected char) rather than crash;
                # the suffix regex already validated the overall shape.
                pos += 1
                continue
            start, end = result.regs[0]
            matches.append(Extensions(ext_string[pos + start : pos + end]))
            pos += end

        return tuple(matches)

    @staticmethod
    def _normalize_seventh(token: str) -> str:
        # iReal uses a bare "^" as shorthand for a major 7th ("C^" == "C^7").
        if token == "^":
            return "^7"
        return token or ""

    @classmethod
    @cache
    def _parse_chord_string(cls, raw_chord, substitution=False) -> ChordAttrs:
        # Robustness contract: a malformed chord string must raise exactly one
        # catchable InvalidChordStringException -- never a raw ValueError /
        # IndexError / KeyError / TypeError leaking from enum construction,
        # extension tokenising, or a None/non-str input. The permissive regex can
        # match shapes the downstream parsers reject (e.g. "VIII", "Cadd9add11"),
        # so we funnel every low-level failure through one clean exception.
        try:
            return cls._parse_chord_string_impl(raw_chord, substitution)
        except InvalidChordStringException:
            raise
        except (ValueError, IndexError, KeyError, TypeError) as exc:
            raise InvalidChordStringException(
                f'Attempted to parse "{raw_chord}" which is invalid '
                f'({type(exc).__name__}: {exc})'
            ) from exc

    @classmethod
    def _parse_chord_string_impl(cls, raw_chord, substitution=False) -> ChordAttrs:
        if "/" in raw_chord:
            logger.info("Doesn't currently support slash chords.")
            raw_chord = raw_chord.split("/")[0]
        match_groups = re.match(cls.__regex__, raw_chord)
        AbstractChord._verify_chord_string(raw_chord, match_groups)
        _root = cls._parse_root(match_groups["root"])
        _triad_token = match_groups["triad"]
        # A sus token may surface from any of the three positions; collect it.
        _sus = match_groups["sus1"] or match_groups["sus2"]
        _triad_is_sus = _triad_token in ("sus", "sus4", "sus2")
        if _sus and _triad_token and not _triad_is_sus:
            raise InvalidChordStringException(
                f'Attempted to parse "{raw_chord}": a triad and a sus cannot '
                f"coexist ({_triad_token!r} + {_sus!r})"
            )
        _triad = Triad(_sus or _triad_token or "")
        _7th = Seventh(cls._normalize_seventh(match_groups["seventh"]))

        _ext_token = match_groups["ext"] or ""
        if match_groups["alt"]:
            # An altered dominant is a dominant 7 carrying altered tensions; it is
            # a dominant-only modifier and does not combine with a sus chord
            # (which has no 3rd to alter) -- reject rather than build a chord whose
            # canonical form (`C7susalt`) cannot be re-parsed.
            if _triad in (Triad.Sus, Triad.Sus2, Triad.Sus4):
                raise InvalidChordStringException(
                    f'Attempted to parse "{raw_chord}": "alt" cannot modify a sus chord'
                )
            _7th = Seventh.Minor
            _extensions = (Extensions.alt,) + cls._get_extensions(_ext_token)
        else:
            _extensions = cls._get_extensions(_ext_token)

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
    def _parse_root(cls, match): ...

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
