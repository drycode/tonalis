from abc import ABC
import string
from music_dsl.domain.chords.chord import Chord
from music_dsl.domain.time import TimeSignature
from music_dsl.domain.chords.abstract_chord import AbstractChord


class AbstractBeatContainer(ABC):
    def __init__(self, chord: AbstractChord) -> None:
        self.chord: AbstractChord = chord


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
        beat = None
        for chord in chords_list:
            times = 1 + chord.count("%")
            beat = self.beat_type(0, self.chord_type(chord.strip("%")))
            for _ in range(times):
                write += 1
                self.beat_containers[write] = beat

        while write < self.time_signature.denominator:
            self.beat_containers[write] = beat
            write += 1

    def __repr__(self) -> str:
        return f"{self.beat_containers}"

    def __getitem__(self, item) -> AbstractBeatContainer:
        return self.beat_containers[item]
