import { describe, it, expect } from "vitest";
import { scaleDegreesEqual } from "./index";

describe("ScaleDegree", () => {
  it("enharmonic degree equality (#iv == bv), major/minor distinct", () => {
    expect(scaleDegreesEqual("#iv", "bv")).toBe(true);
    expect(scaleDegreesEqual("#I", "bII")).toBe(true);
    expect(scaleDegreesEqual("II", "ii")).toBe(false);
    expect(scaleDegreesEqual("ii", "iii")).toBe(false);
  });
});
