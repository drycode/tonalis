from enum import Enum


class ScaleDegree(Enum):
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

    major_to_minor = {
        I: i,
        sI: si,
        bII: bii,
        II: ii,
        sII: sii,
        bIII: biii,
        III: iii,
        IV: iv,
        sIV: siv,
        bV: bv,
        V: v,
        sV: sv,
        bVI: bvi,
        VI: vi,
        sVI: svi,
        bVII: bvii,
        VII: vii,
    }

    minor_to_major = {
        i: I,
        si: sI,
        bii: bII,
        ii: II,
        sii: sII,
        biii: bIII,
        iii: III,
        iv: IV,
        siv: sIV,
        bv: bV,
        v: V,
        sv: sV,
        bvi: bVI,
        vi: VI,
        svi: sVI,
        bvii: bVII,
        vii: VII,
    }

    sharps_to_flats = {
        sI: bII,
        si: bii,
        sII: bIII,
        sii: biii,
        sIV: bV,
        siv: bv,
        sV: bVI,
        sv: bvi,
        sVI: bVII,
        svi: bvii,
    }

    flats_to_sharps = {
        bII: sI,
        bii: si,
        bIII: sII,
        biii: sii,
        bV: sIV,
        bv: siv,
        bVI: sV,
        bvi: sv,
        bVII: sVI,
        bvii: svi,
    }

    @property
    def is_minor(self):
        if self.value in ScaleDegree.minor_to_major.value:
            return True
        return False

    @property
    def is_major(self):
        if self.value in ScaleDegree.major_to_minor.value:
            return True
        return False

    @property
    def is_flat(self):
        if self.value in ScaleDegree.flats_to_sharps.value:
            return True
        return False

    @property
    def is_sharps(self):
        if self.value in ScaleDegree.sharps_to_flats.value:
            return True
        return False

    def to_sharp(self):
        if self.value not in ScaleDegree.flats_to_sharps.value:
            return self
        return ScaleDegree(ScaleDegree.flats_to_sharps.value[self.value])

    def to_flat(self):
        if self.value not in ScaleDegree.sharps_to_flats.value:
            return self
        return ScaleDegree(ScaleDegree.sharps_to_flats.value[self.value])

    def to_major(self):
        if self.value not in ScaleDegree.minor_to_major.value:
            return self
        return ScaleDegree(ScaleDegree.minor_to_major.value[self.value])

    def to_minor(self):
        if self.value not in ScaleDegree.major_to_minor.value:
            return self
        return ScaleDegree(ScaleDegree.major_to_minor.value[self.value])

    def normalized(self):
        return self.to_major().to_flat()

    def normalize(self, is_flat, is_minor):
        self = self.to_flat() if is_flat else self.to_sharp()
        self = self.to_minor() if is_minor else self.to_major()
        return self

    def __eq__(self, other):
        enharmonic = ScaleDegree.sharps_to_flats.value.get(
            other.value
        ) or ScaleDegree.flats_to_sharps.value.get(other.value)
        return self.value == other.value or self.value == enharmonic

    def __hash__(self):
        return hash(ScaleDegree.sharps_to_flats.value.get(self.name) or self.name)


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
