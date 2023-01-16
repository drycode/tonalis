import itertools

from music_dsl.domain.static import ScaleDegree, SupportedExtensions, Seventh, Triad


def members(enum):
    return [
        member.value
        for member in enum.__members__.values()
        if member and not isinstance(member.value, dict)
    ]


NUMERIC_CHORD_SUPERSET = [
    "".join(tup)
    for tup in itertools.product(
        members(ScaleDegree),
        members(Triad),
        members(Seventh),
        [member.value for member in SupportedExtensions],
    )
]

EXAMPLE_NUMERIC_STRS = NUMERIC_CHORD_SUPERSET

EXAMPLE_MULTI_DIM_CHORDS = [
    "/".join(tup)
    for tup in itertools.product(NUMERIC_CHORD_SUPERSET, members(ScaleDegree))
]
