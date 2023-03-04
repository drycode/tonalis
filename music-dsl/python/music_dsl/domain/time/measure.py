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

    def __repr__(self) -> str:
        return f"m.{self.measure_number} - beat: {self.beat_number}"


@dataclass(frozen=True)
class MeasurelessBeatLocation(AbstractBeatLocation):
    beat_number: int
    measure_number: Literal[-1] = -1

    def __repr__(self) -> str:
        return f"m.{self.measure_number} - beat: {self.beat_number}"


class BeatType(AbstractBeatContainer):
    def __init__(self, beat_location: BeatLocation, chord: Chord) -> None:
        self.beat_location: BeatLocation = beat_location
        self.chord: Chord = chord

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
        self.beat_containers = [None] * time_signature.denominator
        self._setup_beats(delimiter)

    def _setup_beats(self, delimiter=" "):
        chords_list = self.raw_measure.replace(delimiter, "% ").split(delimiter)
        while chords_list[-1] == "":
            chords_list.pop()
        write = -1
        for chord in chords_list:
            times = 1 + chord.count("%")
            for _ in range(times):
                write += 1
                self.beat_containers[write] = self.beat_type(
                    BeatLocation(self.m_number, write),
                    self.chord_type(chord.strip("%")),
                )

        while write < self.time_signature.denominator:
            self.beat_containers[write] = self.beat_type(
                BeatLocation(self.m_number, write),
                self.chord_type(chord.strip("%")),
            )
            write += 1

    def __repr__(self) -> str:
        return f"{self.beat_containers}"

    def __getitem__(self, item) -> AbstractBeatContainer:
        return self.beat_containers[item]
