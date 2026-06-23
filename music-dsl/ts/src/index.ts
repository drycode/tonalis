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
  Scales,
  scaleValue,
  encodingValue,
} from "./encode.js";

export {
  InvalidChordStringError,
  type ChordModel,
  type ChordSerialized,
  parseChord,
  serializeChord,
  chordEncoding,
} from "./chord.js";

export {
  IncorrectHarmonicFunctionError,
  type NumericChordAttrs,
  type NumericChordModel,
  type NumericChordSerialized,
  fromChordString,
  fromChord,
  serializeNumericChord,
  SUBSTITUTE_RESOLUTIONS,
  DOMINANT_RESOLUTIONS,
  SUBDOMINANT_RESOLUTIONS,
  MAJOR_HARMONIC_FUNCTIONS,
} from "./numericChord.js";

export {
  modulate,
  isDiatonic,
  harmonicFunctionInKey,
  chordInKey,
} from "./transactions.js";

export {
  noteToMidi,
  midiToHz,
  intervalPitches,
  chordPitches,
  scalePitches,
  scaleDegreePitch,
} from "./realize.js";

export {
  type TimeSignature,
  type BeatLocation,
  type BeatContainer,
  type MeasureModel,
  parseMeasure,
  serializeMeasure,
} from "./measure.js";
