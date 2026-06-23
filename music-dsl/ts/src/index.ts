/**
 * music_dsl — public API re-exports.
 * All static music-theory domain objects for the TS port.
 */

export {
  type Note,
  TWELVE_TONES,
  noteValue,
  noteFromValue,
  noteToFlat,
  notesEqual,
  noteIndex,
} from "./notes.js";

export {
  type IntervalName,
  intervalSemitones,
  intervalsEqual,
} from "./intervals.js";

export {
  type ScaleDegreeT,
  SCALE_DEGREES,
  scaleDegreesEqual,
  scaleDegreeIndex,
} from "./scaleDegree.js";

export {
  HarmonicFunction,
  type HarmonicFunction as HarmonicFunctionT,
  Triad,
  type Triad as TriadT,
  Seventh,
  type Seventh as SeventhT,
  Extensions,
  type Extensions as ExtensionsT,
} from "./chordQuality.js";

export {
  MIN_SUPPORTED,
  MAX_SUPPORTED,
  stripLeft,
  stripRight,
  semitonesApartAscending,
} from "./helpers.js";

export {
  EMPTY_CHORD_ENCODING,
  DIMINISHED_ENCODING,
  ENCODING_MAP,
  Scales,
  scaleValue,
  encodingValue,
} from "./encode.js";
