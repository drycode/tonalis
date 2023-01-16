from dataclasses import dataclass
from .chord import HarmonicFunctions, Seventh, Triad
from .notes import Intervals, Notes


# MAJOR = {
#     Intervals.Unison: ChordAttrs(
#         None, Triad.Major, Seventh.Major, None, HarmonicFunctions.Tonic
#     ),
#     Intervals.M2: ChordAttrs(
#         None, Triad.Minor, Seventh.Minor, None, HarmonicFunctions.Subdominant
#     ),
#     Intervals.M3: ChordAttrs(
#         None, Triad.Minor, Seventh.Minor, None, HarmonicFunctions.Tonic
#     ),
#     Intervals.P4: ChordAttrs(
#         None, Triad.Major, Seventh.Major, None, HarmonicFunctions.Subdominant
#     ),
#     Intervals.P5: ChordAttrs(
#         None, Triad.Major, Seventh.Minor, None, HarmonicFunctions.Dominant
#     ),
#     Intervals.M6: ChordAttrs(
#         None, Triad.Minor, Seventh.Minor, None, HarmonicFunctions.Tonic
#     ),
#     Intervals.M7: ChordAttrs(
#         None, Triad.HalfDiminished, Seventh.Minor, None, HarmonicFunctions.Dominant
#     ),
# }


# def add_enharmonics(scale):
#     scale.update({key.enharmonic(): value for key, value in scale.items()})


# add_enharmonics(MAJOR)
