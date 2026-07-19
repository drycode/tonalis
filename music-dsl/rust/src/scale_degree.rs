//! ScaleDegree — the 34-member Roman numeral degree set.
//! `==` is structural (derived). Enharmonic equality is `scale_degrees_equal()` in lib.rs.

/// 34 scale degree values (major + minor × natural + sharp + flat).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ScaleDegree {
    I,
    Ii,    // i
    SI,    // #I
    Si,    // #i
    BII,   // bII
    Bii,   // bii
    II,
    Iimin, // ii
    SII,   // #II
    Sii,   // #ii
    BIII,  // bIII
    Biii,  // biii
    III,
    Iiimin, // iii
    IV,
    Ivmin,  // iv
    SIV,    // #IV
    Siv,    // #iv
    BV,     // bV
    Bv,     // bv
    V,
    Vmin,   // v
    SV,     // #V
    Sv,     // #v
    BVI,    // bVI
    Bvi,    // bvi
    VI,
    Vimin,  // vi
    SVII,   // #VI (named SVII to match pattern but val="#VI")
    Svii,   // #vi (val="#vi")
    BVII,   // bVII
    Bvii,   // bvii
    VII,
    Viimin, // vii
}

impl ScaleDegree {
    /// Parse from the value string (e.g. `"#iv"`, `"bV"`, `"ii"`).
    pub fn from_value(s: &str) -> Option<Self> {
        match s {
            "I"    => Some(ScaleDegree::I),
            "i"    => Some(ScaleDegree::Ii),
            "#I"   => Some(ScaleDegree::SI),
            "#i"   => Some(ScaleDegree::Si),
            "bII"  => Some(ScaleDegree::BII),
            "bii"  => Some(ScaleDegree::Bii),
            "II"   => Some(ScaleDegree::II),
            "ii"   => Some(ScaleDegree::Iimin),
            "#II"  => Some(ScaleDegree::SII),
            "#ii"  => Some(ScaleDegree::Sii),
            "bIII" => Some(ScaleDegree::BIII),
            "biii" => Some(ScaleDegree::Biii),
            "III"  => Some(ScaleDegree::III),
            "iii"  => Some(ScaleDegree::Iiimin),
            "IV"   => Some(ScaleDegree::IV),
            "iv"   => Some(ScaleDegree::Ivmin),
            "#IV"  => Some(ScaleDegree::SIV),
            "#iv"  => Some(ScaleDegree::Siv),
            "bV"   => Some(ScaleDegree::BV),
            "bv"   => Some(ScaleDegree::Bv),
            "V"    => Some(ScaleDegree::V),
            "v"    => Some(ScaleDegree::Vmin),
            "#V"   => Some(ScaleDegree::SV),
            "#v"   => Some(ScaleDegree::Sv),
            "bVI"  => Some(ScaleDegree::BVI),
            "bvi"  => Some(ScaleDegree::Bvi),
            "VI"   => Some(ScaleDegree::VI),
            "vi"   => Some(ScaleDegree::Vimin),
            "#VI"  => Some(ScaleDegree::SVII),
            "#vi"  => Some(ScaleDegree::Svii),
            "bVII" => Some(ScaleDegree::BVII),
            "bvii" => Some(ScaleDegree::Bvii),
            "VII"  => Some(ScaleDegree::VII),
            "vii"  => Some(ScaleDegree::Viimin),
            _      => None,
        }
    }

    /// Display value string.
    pub fn value(self) -> &'static str {
        match self {
            ScaleDegree::I      => "I",
            ScaleDegree::Ii     => "i",
            ScaleDegree::SI     => "#I",
            ScaleDegree::Si     => "#i",
            ScaleDegree::BII    => "bII",
            ScaleDegree::Bii    => "bii",
            ScaleDegree::II     => "II",
            ScaleDegree::Iimin  => "ii",
            ScaleDegree::SII    => "#II",
            ScaleDegree::Sii    => "#ii",
            ScaleDegree::BIII   => "bIII",
            ScaleDegree::Biii   => "biii",
            ScaleDegree::III    => "III",
            ScaleDegree::Iiimin => "iii",
            ScaleDegree::IV     => "IV",
            ScaleDegree::Ivmin  => "iv",
            ScaleDegree::SIV    => "#IV",
            ScaleDegree::Siv    => "#iv",
            ScaleDegree::BV     => "bV",
            ScaleDegree::Bv     => "bv",
            ScaleDegree::V      => "V",
            ScaleDegree::Vmin   => "v",
            ScaleDegree::SV     => "#V",
            ScaleDegree::Sv     => "#v",
            ScaleDegree::BVI    => "bVI",
            ScaleDegree::Bvi    => "bvi",
            ScaleDegree::VI     => "VI",
            ScaleDegree::Vimin  => "vi",
            ScaleDegree::SVII   => "#VI",
            ScaleDegree::Svii   => "#vi",
            ScaleDegree::BVII   => "bVII",
            ScaleDegree::Bvii   => "bvii",
            ScaleDegree::VII    => "VII",
            ScaleDegree::Viimin => "vii",
        }
    }

    /// Convert a sharp degree to its flat equivalent; natural/flat → self.
    pub fn to_flat(self) -> Self {
        match self {
            ScaleDegree::SI   => ScaleDegree::BII,
            ScaleDegree::Si   => ScaleDegree::Bii,
            ScaleDegree::SII  => ScaleDegree::BIII,
            ScaleDegree::Sii  => ScaleDegree::Biii,
            ScaleDegree::SIV  => ScaleDegree::BV,
            ScaleDegree::Siv  => ScaleDegree::Bv,
            ScaleDegree::SV   => ScaleDegree::BVI,
            ScaleDegree::Sv   => ScaleDegree::Bvi,
            ScaleDegree::SVII => ScaleDegree::BVII,
            ScaleDegree::Svii => ScaleDegree::Bvii,
            other             => other,
        }
    }

    /// Convert a flat degree to its sharp equivalent; natural/sharp → self.
    pub fn to_sharp(self) -> Self {
        match self {
            ScaleDegree::BII  => ScaleDegree::SI,
            ScaleDegree::Bii  => ScaleDegree::Si,
            ScaleDegree::BIII => ScaleDegree::SII,
            ScaleDegree::Biii => ScaleDegree::Sii,
            ScaleDegree::BV   => ScaleDegree::SIV,
            ScaleDegree::Bv   => ScaleDegree::Siv,
            ScaleDegree::BVI  => ScaleDegree::SV,
            ScaleDegree::Bvi  => ScaleDegree::Sv,
            ScaleDegree::BVII => ScaleDegree::SVII,
            ScaleDegree::Bvii => ScaleDegree::Svii,
            other             => other,
        }
    }

    /// Convert minor to major (case-lifting); major → self.
    pub fn to_major(self) -> Self {
        match self {
            ScaleDegree::Ii     => ScaleDegree::I,
            ScaleDegree::Si     => ScaleDegree::SI,
            ScaleDegree::Bii    => ScaleDegree::BII,
            ScaleDegree::Iimin  => ScaleDegree::II,
            ScaleDegree::Sii    => ScaleDegree::SII,
            ScaleDegree::Biii   => ScaleDegree::BIII,
            ScaleDegree::Iiimin => ScaleDegree::III,
            ScaleDegree::Ivmin  => ScaleDegree::IV,
            ScaleDegree::Siv    => ScaleDegree::SIV,
            ScaleDegree::Bv     => ScaleDegree::BV,
            ScaleDegree::Vmin   => ScaleDegree::V,
            ScaleDegree::Sv     => ScaleDegree::SV,
            ScaleDegree::Bvi    => ScaleDegree::BVI,
            ScaleDegree::Vimin  => ScaleDegree::VI,
            ScaleDegree::Svii   => ScaleDegree::SVII,
            ScaleDegree::Bvii   => ScaleDegree::BVII,
            ScaleDegree::Viimin => ScaleDegree::VII,
            other               => other,
        }
    }

    /// `normalized()` = `to_major().to_flat()`.
    pub fn normalized(self) -> Self {
        self.to_major().to_flat()
    }

    /// True if this degree's value string starts with `'b'` (flat prefix).
    pub fn is_flat(self) -> bool {
        self.value().starts_with('b')
    }

    /// True if this degree uses lowercase Roman numerals (minor quality).
    pub fn is_minor(self) -> bool {
        let v = self.value();
        let alpha = v.trim_start_matches(['b', '#']);
        alpha.chars().next().map(|c| c.is_lowercase()).unwrap_or(false)
    }

    /// Apply accidental and case to this degree (which should be in flat-major form from SCALE_DEGREES).
    ///
    /// Mirrors Python `ScaleDegree.normalize(is_flat, is_minor)`:
    /// - if `is_flat`: keep flat (or convert sharp→flat); else convert flat→sharp
    /// - if `is_minor`: convert to minor case; else keep major
    pub fn normalize(self, is_flat: bool, is_minor: bool) -> Self {
        let accidental = if is_flat { self.to_flat() } else { self.to_sharp() };
        if is_minor { accidental.to_minor() } else { accidental }
    }

    /// Convert major degree to its minor (lowercase) equivalent; minor → self.
    pub fn to_minor(self) -> Self {
        match self {
            ScaleDegree::I     => ScaleDegree::Ii,
            ScaleDegree::SI    => ScaleDegree::Si,
            ScaleDegree::BII   => ScaleDegree::Bii,
            ScaleDegree::II    => ScaleDegree::Iimin,
            ScaleDegree::SII   => ScaleDegree::Sii,
            ScaleDegree::BIII  => ScaleDegree::Biii,
            ScaleDegree::III   => ScaleDegree::Iiimin,
            ScaleDegree::IV    => ScaleDegree::Ivmin,
            ScaleDegree::SIV   => ScaleDegree::Siv,
            ScaleDegree::BV    => ScaleDegree::Bv,
            ScaleDegree::V     => ScaleDegree::Vmin,
            ScaleDegree::SV    => ScaleDegree::Sv,
            ScaleDegree::BVI   => ScaleDegree::Bvi,
            ScaleDegree::VI    => ScaleDegree::Vimin,
            ScaleDegree::SVII  => ScaleDegree::Svii,
            ScaleDegree::BVII  => ScaleDegree::Bvii,
            ScaleDegree::VII   => ScaleDegree::Viimin,
            other              => other, // already minor
        }
    }

    /// Chromatic index 0–11 in the SCALE_DEGREES flat-major ordering.
    /// Works by normalizing to major-flat and doing a positional lookup.
    pub fn scale_degree_index(self) -> i64 {
        let norm = self.normalized();
        match norm {
            ScaleDegree::I    => 0,
            ScaleDegree::BII  => 1,
            ScaleDegree::II   => 2,
            ScaleDegree::BIII => 3,
            ScaleDegree::III  => 4,
            ScaleDegree::IV   => 5,
            ScaleDegree::BV   => 6,
            ScaleDegree::V    => 7,
            ScaleDegree::BVI  => 8,
            ScaleDegree::VI   => 9,
            ScaleDegree::BVII => 10,
            ScaleDegree::VII  => 11,
            // All minor/sharp inputs are normalized above; this branch is unreachable
            // for valid input, but we need exhaustive coverage.
            _ => panic!("normalized() produced non-flat-major degree: {:?}", norm),
        }
    }
}

/// The 12 scale degrees in flat-major form at chromatic positions 0-11.
/// Index 0 = I, 1 = bII, 2 = II, ... 11 = VII.
pub static SCALE_DEGREES: [ScaleDegree; 12] = [
    ScaleDegree::I,
    ScaleDegree::BII,
    ScaleDegree::II,
    ScaleDegree::BIII,
    ScaleDegree::III,
    ScaleDegree::IV,
    ScaleDegree::BV,
    ScaleDegree::V,
    ScaleDegree::BVI,
    ScaleDegree::VI,
    ScaleDegree::BVII,
    ScaleDegree::VII,
];
