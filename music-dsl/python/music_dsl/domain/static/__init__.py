from types import SimpleNamespace
from .chord import *
from .notes import *
from .scale_degree import *


# .up() and .down() represents the direction of resolution and should not be
# removed without extreme care
SUBSTITUTE_RESOLUTIONS = {
    Intervals.m2.down(),
    Intervals.M7.up(),
}

DOMINANT_RESOLUTIONS = {
    *SUBSTITUTE_RESOLUTIONS,
    Intervals.P5.up(),
    Intervals.P4.up(),
    Intervals.M2.up(),
    Intervals.m7.down(),
}

SUBDOMINANT_RESOLUTIONS = (
    SUBSTITUTE_RESOLUTIONS.copy()
    ^ DOMINANT_RESOLUTIONS.copy()
    ^ {
        Intervals.M2.up(),
        Intervals.M7.up(),
    }
)


MAJOR_HARMONIC_FUNCTIONS = SimpleNamespace(
    tonic={
        Intervals.M3.up(),
        Intervals.m6.down(),
        Intervals.M6.up(),
        Intervals.m3.down(),
    },
    dominant={
        Intervals.M7.up(),
        Intervals.m2.down(),
        Intervals.P5.up(),
        Intervals.P4.down(),
    },
    subdominant={
        Intervals.M2.up(),
        Intervals.m7.down(),
        Intervals.P4.up(),
        Intervals.P5.down(),
    },
)
