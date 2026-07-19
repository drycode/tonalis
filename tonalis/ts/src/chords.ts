/**
 * Chord-token validation for the lead-sheet linter, standing on music_dsl.
 *
 * Replaces chordGrammar's hand-rolled regex: the "is this a real chord" decision is delegated to
 * music_dsl's parseChord (the theory library is the single source of truth for what a chord is).
 * The non-chord lead-sheet tokens parseChord rightly rejects but the linter must accept are kept:
 *   - "N.C." / "n"      — explicit no-chord markers.
 *   - a standalone slash-bass continuation ("/A") — a carried-over bass note, no quality.
 *   - the augmented layout-star artifact ("Bb*7+*") — lead-sheet notation glues a "*"; strip it before validating.
 *
 * One-way dependency rule (Phase 1/3): leadsheet -> music_dsl; music_dsl must never import leadsheet.
 */
import { parseChord, InvalidChordStringError } from "@tonalis/music-dsl";

const SLASH_BASS = /^\/[A-G][b#]?$/; // standalone bass continuation, e.g. /A

/** True iff the token is a well-formed chord OR a no-chord / bass marker. */
export function isValidChord(token: string): boolean {
  if (token === "N.C." || token === "n") return true;
  if (!token) return false;
  const t = token.replace(/\*/g, ""); // tolerate the augmented layout-star artifact (Bb*7+*)
  if (SLASH_BASS.test(t)) return true;
  try {
    parseChord(t);
    return true;
  } catch (e) {
    if (e instanceof InvalidChordStringError) return false;
    throw e; // never mask an unrelated error as "invalid chord"
  }
}
