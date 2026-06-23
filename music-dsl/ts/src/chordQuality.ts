/**
 * Chord-quality enums — const objects preserving verbatim Python reference values.
 * Port of music_dsl/domain/static/chord.py.
 */

/** HarmonicFunction — serializes by name (not integer). */
export const HarmonicFunction = {
  Dominant:    "Dominant",
  Subdominant: "Subdominant",
  Tonic:       "Tonic",
} as const;
export type HarmonicFunction = typeof HarmonicFunction[keyof typeof HarmonicFunction];

/** Triad quality values (verbatim from reference: Major is the empty string). */
export const Triad = {
  Major:           "",
  Minor:           "-",
  HalfDiminished:  "h",
  Diminished:      "o",
  Augmented:       "+",
  Sus:             "sus",
  Sus2:            "sus2",
  Sus4:            "sus4",
} as const;
export type Triad = typeof Triad[keyof typeof Triad];

/** Seventh quality values (Major = "^7", None = ""). */
export const Seventh = {
  Major: "^7",
  Minor: "7",
  _None: "",
} as const;
export type Seventh = typeof Seventh[keyof typeof Seventh];

/** Extension values — 16-member set. */
export const Extensions = {
  _None: "",
  add2:  "2",
  add3:  "3",
  b5:    "b5",
  add5:  "5",
  s5:    "#5",
  b6:    "b6",
  add6:  "6",
  b9:    "b9",
  add9:  "9",
  s9:    "#9",
  add11: "11",
  s11:   "#11",
  b13:   "b13",
  add13: "13",
  alt:   "alt",
} as const;
export type Extensions = typeof Extensions[keyof typeof Extensions];
