import { describe, expect, it } from "vitest";
import { tranchesDue } from "../src/vesting";

const g = { grantId: "g1", holderId: "h1", shares: 4800, start: "2025-01-15", months: 48, cliffMonths: 12 };

describe("vesting schedule", () => {
  it("vests nothing before the cliff", () => {
    expect(tranchesDue(g, "2025-12-14")).toEqual([]);
  });
  it("catches up the cliff, then vests monthly", () => {
    const t = tranchesDue(g, "2026-01-15");
    expect(t).toHaveLength(12);
    expect(t.reduce((s, x) => s + x.shares, 0)).toBe(1200);
    expect(t[11]?.vestsOn).toBe("2026-01-15");
  });
  it("vests the whole grant by the end, remainder in the last tranche", () => {
    const odd = { ...g, shares: 1001 };
    const t = tranchesDue(odd, "2030-01-01");
    expect(t).toHaveLength(48);
    expect(t.reduce((s, x) => s + x.shares, 0)).toBe(1001);
  });
});
