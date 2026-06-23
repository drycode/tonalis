import { describe, it, expect } from "vitest";
import { Triad, Seventh, Extensions } from "./index";

describe("chord-quality enum values (verbatim from reference)", () => {
  it("Triad.Major is the empty string; sus variants present", () => {
    expect(Triad.Major).toBe("");
    expect(Triad.Minor).toBe("-");
    expect(Triad.HalfDiminished).toBe("h");
    expect(Triad.Diminished).toBe("o");
    expect(Triad.Sus4).toBe("sus4");
  });
  it("Seventh.Major is ^7, not maj7", () => {
    expect(Seventh.Major).toBe("^7");
    expect(Seventh.Minor).toBe("7");
  });
  it("Extensions cover the 16-member value set", () => {
    expect(Extensions.s11).toBe("#11");
    expect(Extensions.b9).toBe("b9");
    expect(Extensions.alt).toBe("alt");
  });
});
