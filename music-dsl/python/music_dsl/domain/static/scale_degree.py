from music_dsl.utils import JsonSerializableEnum

# Roman-numeral spelling maps, keyed by degree string value. Defined at module
# level (NOT inside the Enum body) so they don't become ScaleDegree members — a
# dict assigned in an Enum class body is turned into a member and pollutes
# iteration/len. The `_MINOR_TO_MAJOR` / `_FLATS_TO_SHARPS` inverses are derived,
# so the two directions can't drift.
_MAJOR_TO_MINOR = {
    "I": "i", "#I": "#i", "bII": "bii", "II": "ii", "#II": "#ii",
    "bIII": "biii", "III": "iii", "IV": "iv", "#IV": "#iv", "bV": "bv",
    "V": "v", "#V": "#v", "bVI": "bvi", "VI": "vi", "#VI": "#vi",
    "bVII": "bvii", "VII": "vii",
}
_MINOR_TO_MAJOR = {minor: major for major, minor in _MAJOR_TO_MINOR.items()}

_SHARPS_TO_FLATS = {
    "#I": "bII", "#i": "bii", "#II": "bIII", "#ii": "biii", "#IV": "bV",
    "#iv": "bv", "#V": "bVI", "#v": "bvi", "#VI": "bVII", "#vi": "bvii",
}
_FLATS_TO_SHARPS = {flat: sharp for sharp, flat in _SHARPS_TO_FLATS.items()}


class ScaleDegree(JsonSerializableEnum):
    I = "I"
    i = "i"
    sI = "#I"
    si = "#i"
    bII = "bII"
    bii = "bii"
    II = "II"
    ii = "ii"
    sII = "#II"
    sii = "#ii"
    bIII = "bIII"
    biii = "biii"
    III = "III"
    iii = "iii"
    IV = "IV"
    iv = "iv"
    sIV = "#IV"
    siv = "#iv"
    bV = "bV"
    bv = "bv"
    V = "V"
    v = "v"
    sV = "#V"
    sv = "#v"
    bVI = "bVI"
    bvi = "bvi"
    VI = "VI"
    vi = "vi"
    sVI = "#VI"
    svi = "#vi"
    bVII = "bVII"
    bvii = "bvii"
    VII = "VII"
    vii = "vii"

    @property
    def is_minor(self):
        if self.value in _MINOR_TO_MAJOR:
            return True
        return False

    @property
    def is_major(self):
        if self.value in _MAJOR_TO_MINOR:
            return True
        return False

    @property
    def is_flat(self):
        if self.value in _FLATS_TO_SHARPS:
            return True
        return False

    @property
    def is_sharps(self):
        if self.value in _SHARPS_TO_FLATS:
            return True
        return False

    def to_sharp(self):
        if self.value not in _FLATS_TO_SHARPS:
            return self
        return ScaleDegree(_FLATS_TO_SHARPS[self.value])

    def to_flat(self):
        if self.value not in _SHARPS_TO_FLATS:
            return self
        return ScaleDegree(_SHARPS_TO_FLATS[self.value])

    def to_major(self):
        if self.value not in _MINOR_TO_MAJOR:
            return self
        return ScaleDegree(_MINOR_TO_MAJOR[self.value])

    def to_minor(self):
        if self.value not in _MAJOR_TO_MINOR:
            return self
        return ScaleDegree(_MAJOR_TO_MINOR[self.value])

    def normalized(self):
        return self.to_major().to_flat()

    def normalize(self, is_flat, is_minor):
        self = self.to_flat() if is_flat else self.to_sharp()
        self = self.to_minor() if is_minor else self.to_major()
        return self

    def __eq__(self, other):
        if not isinstance(other, ScaleDegree):
            return NotImplemented  # sd == None / str / Notes → False, not a crash
        enharmonic = _SHARPS_TO_FLATS.get(
            other.value
        ) or _FLATS_TO_SHARPS.get(other.value)
        return self.value == other.value or self.value == enharmonic

    def __hash__(self):
        # Consistent with the enharmonic __eq__: a sharp degree normalizes to its flat
        # spelling so enharmonic-equal degrees hash equal. (Major/minor stay distinct,
        # matching __eq__, which does not equate them.)
        return hash(_SHARPS_TO_FLATS.get(self.value, self.value))


SCALE_DEGREES = [
    ScaleDegree.I,
    ScaleDegree.bII,
    ScaleDegree.II,
    ScaleDegree.bIII,
    ScaleDegree.III,
    ScaleDegree.IV,
    ScaleDegree.bV,
    ScaleDegree.V,
    ScaleDegree.bVI,
    ScaleDegree.VI,
    ScaleDegree.bVII,
    ScaleDegree.VII,
]
