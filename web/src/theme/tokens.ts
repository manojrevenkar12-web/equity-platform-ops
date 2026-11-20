/**
 * Tokens for the platform dashboard. A cool concrete ground and petrol ink, like a status board in a server
 * room; one deep teal, the colour of a passing check, for focus and the active view. The as-found org is
 * orange and the platform blue in every view; ablations are grey. The six places engineering hours go use the
 * validated categorical order (slots 1-6), always with a legend and the numbers in a table beside them.
 * Decisions of the plan guard carry a word as well as a colour. Every colour, size and duration comes from here.
 */
export const color = {
  ground: "#EEF1F4",
  sheet: "#FFFFFF",
  ink: "#13202B",
  copy: "#2B3945",
  muted: "#55636F",
  line: "#D3DAE1",
  focus: "#0F6B5C",
  good: "#15663F",
  goodWash: "#DDF0E5",
  warn: "#8A5300",
  warnWash: "#FBEFD9",
  bad: "#B42318",
  badWash: "#FBE4E1",
  platform: "#1D4ED8",
  asFound: "#C2410C",
  ablation: "#A0A8B0",
  part1: "#2a78d6",
  part2: "#eb6834",
  part3: "#1baf7a",
  part4: "#eda100",
  part5: "#e87ba4",
  part6: "#008300",
} as const;

export const font = {
  ui: ["Hanken Grotesk Variable", "Hanken Grotesk", "system-ui", "sans-serif"],
  code: ["JetBrains Mono", "ui-monospace", "monospace"],
} as const;

/** 1.25 ratio from a 15px base. [size, line-height] */
export const type = {
  small: ["0.8125rem", "1.4"],
  body: ["0.9375rem", "1.55"],
  lead: ["1.1875rem", "1.4"],
  title: ["1.875rem", "1.15"],
  hero: ["2.5rem", "1.1"],
} as const;

export const space = { 0: "0", 1: "0.25rem", 2: "0.5rem", 3: "0.75rem", 4: "1rem", 5: "1.5rem", 6: "2rem", 7: "3rem", 8: "4rem" } as const;
export const radius = { none: "0", soft: "4px", card: "8px", pill: "999px" } as const;
export const measure = { prose: "68ch", page: "78rem", hero: "52rem", table: "60rem" } as const;
export const line = { hair: "1px", rule: "2px" } as const;
export const size = { swatch: "0.625rem", bar: "1.75rem", label: "13rem" } as const;
