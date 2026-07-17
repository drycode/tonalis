//! Chord-quality enums: HarmonicFunction, Triad, Seventh, Extensions.
//! All use structural `==` (derived PartialEq). Values match the Python reference verbatim.

/// The three harmonic functions. Auto-numbered 1–3 matching Python `auto()`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum HarmonicFunction {
    Dominant   = 1,
    Subdominant = 2,
    Tonic      = 3,
}

impl HarmonicFunction {
    /// Serializes by name (matches Python `JsonSerializableEnum.to_json → _name_`).
    pub fn name(self) -> &'static str {
        match self {
            HarmonicFunction::Dominant    => "Dominant",
            HarmonicFunction::Subdominant => "Subdominant",
            HarmonicFunction::Tonic       => "Tonic",
        }
    }

    /// Inverse of [`HarmonicFunction::name`]: parse a member name back to the enum.
    pub(crate) fn from_name(name: &str) -> Option<Self> {
        match name {
            "Dominant"    => Some(HarmonicFunction::Dominant),
            "Subdominant" => Some(HarmonicFunction::Subdominant),
            "Tonic"       => Some(HarmonicFunction::Tonic),
            _             => None,
        }
    }
}

/// Triad quality. `Major.value() == ""`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Triad {
    Major,
    Minor,
    HalfDiminished,
    Diminished,
    Augmented,
    Sus,
    Sus2,
    Sus4,
}

impl Triad {
    pub fn value(self) -> &'static str {
        match self {
            Triad::Major           => "",
            Triad::Minor           => "-",
            Triad::HalfDiminished  => "h",
            Triad::Diminished      => "o",
            Triad::Augmented       => "+",
            Triad::Sus             => "sus",
            Triad::Sus2            => "sus2",
            Triad::Sus4            => "sus4",
        }
    }
}

/// Seventh quality. `Major.value() == "^7"`, `_None.value() == ""`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Seventh {
    Major,
    Minor,
    None,
}

impl Seventh {
    pub fn value(self) -> &'static str {
        match self {
            Seventh::Major => "^7",
            Seventh::Minor => "7",
            Seventh::None  => "",
        }
    }
}

/// Chord extension/tension. 16 members.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Extensions {
    None,
    Add2,
    Add3,
    B5,
    Add5,
    S5,
    B6,
    Add6,
    B9,
    Add9,
    S9,
    Add11,
    S11,
    B13,
    Add13,
    Alt,
}

impl Extensions {
    pub fn value(self) -> &'static str {
        match self {
            Extensions::None  => "",
            Extensions::Add2  => "2",
            Extensions::Add3  => "3",
            Extensions::B5    => "b5",
            Extensions::Add5  => "5",
            Extensions::S5    => "#5",
            Extensions::B6    => "b6",
            Extensions::Add6  => "6",
            Extensions::B9    => "b9",
            Extensions::Add9  => "9",
            Extensions::S9    => "#9",
            Extensions::Add11 => "11",
            Extensions::S11   => "#11",
            Extensions::B13   => "b13",
            Extensions::Add13 => "13",
            Extensions::Alt   => "alt",
        }
    }
}
