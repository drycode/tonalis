/**
 * Deprecated: chord validation moved to ./chords.ts (music_dsl-backed). Kept as a re-export shim so
 * any `import { isValidChord } from "./chordGrammar.js"` still resolves. No chord regex remains here.
 */
export { isValidChord } from "./chords.js";
