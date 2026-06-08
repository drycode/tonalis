from abc import ABC
from dataclasses import dataclass
import string
from typing import Literal
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.time import TimeSignature
from music_dsl.domain.chords.abstract_chord import AbstractChord


class AbstractBeatLocation(ABC):
    measure_number: int
    beat_number: int


class AbstractBeatContainer(ABC):
    def __init__(
        self, beat_location: AbstractBeatLocation, chord: AbstractChord
    ) -> None:
        self.chord: AbstractChord = chord
        self.beat_location: AbstractBeatLocation = beat_location


@dataclass(frozen=True)
class BeatLocation(AbstractBeatLocation):
    measure_number: int
    beat_number: int

    def to_json(self):
        return self.__dict__

    def __repr__(self) -> str:
        return f"m.{self.measure_number} - beat: {self.beat_number}"


@dataclass(frozen=True)
class MeasurelessBeatLocation(AbstractBeatLocation):
    beat_number: int
    measure_number: Literal[-1] = -1

    def to_json(self):
        return {"measureless_beat_number": self.beat_number}

    def __repr__(self) -> str:
        return f"m.{self.measure_number} - beat: {self.beat_number}"


class BeatType(AbstractBeatContainer):
    def __init__(self, beat_location: BeatLocation, chord: Chord) -> None:
        self.beat_location: BeatLocation = beat_location
        self.chord: Chord = chord

    def to_json(self):
        return {
            key: val for key, val in self.__dict__.items() if not key.startswith("_")
        }

    def __eq__(self, __o: object) -> bool:
        return self.beat_location == __o.beat_location and self.chord == __o.chord


class Measure:
    def __init__(
        self,
        m_number: int,
        time_signature: TimeSignature,
        raw_measure: str,
        beat_type: AbstractBeatContainer,
        chord_type: AbstractChord,
        delimiter=" ",
    ):
        self.beat_type = beat_type
        self.chord_type = chord_type
        self.m_number = m_number
        self.raw_measure = raw_measure
        self.time_signature = time_signature
        # beat_containers is sized dynamically in _setup_beats so that measures
        # carrying more chord-beats than the time signature's denominator (e.g.
        # "F^7 Eh A7" expanding to 5 beats in 4/4) do not overflow the array.
        self.beat_containers = []
        self._setup_beats(delimiter)

    def to_json(self):
        result = self.__dict__
        result["beat_type"] = str(self.beat_type)
        result["chord_type"] = str(self.chord_type)
        return result

    def _setup_beats(self, delimiter=" "):
        chords_list = self.raw_measure.replace(delimiter, "% ").split(delimiter)
        while chords_list and chords_list[-1] == "":
            chords_list.pop()

        # Total beats requested by the chord tokens; a measure may legitimately
        # ask for more beats than the denominator (multiple chords per beat),
        # so size the backing list to accommodate the larger of the two.
        total_beats = sum(1 + chord.count("%") for chord in chords_list)
        denominator = self.time_signature.denominator
        size = max(denominator, total_beats)
        self.beat_containers = [None] * size

        write = 0
        last_chord = None
        for chord in chords_list:
            last_chord = chord.strip("%")
            times = 1 + chord.count("%")
            for _ in range(times):
                self.beat_containers[write] = self.beat_type(
                    BeatLocation(self.m_number, write),
                    self.chord_type(last_chord),
                )
                write += 1

        # Pad any remaining slots (when total_beats < denominator) with the LAST
        # chord seen so the measure spans the full bar. Uses last_chord rather
        # than the loop variable to avoid reusing a stale token. If the measure
        # had no chords at all there is nothing to pad with, so leave the
        # remaining slots as None.
        while last_chord is not None and write < size:
            self.beat_containers[write] = self.beat_type(
                BeatLocation(self.m_number, write),
                self.chord_type(last_chord),
            )
            write += 1

    def __repr__(self) -> str:
        return f"{self.beat_containers}"

    def __getitem__(self, item) -> AbstractBeatContainer:
        return self.beat_containers[item]
