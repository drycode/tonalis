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
