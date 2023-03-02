from dataclasses import dataclass

from music_dsl.domain.static.notes import Notes
from music_dsl.encode import Scales


@dataclass
class Key:
    root: Notes
    scale: Scales


__version__ = "0.4.2"
