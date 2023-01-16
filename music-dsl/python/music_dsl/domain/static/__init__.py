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
