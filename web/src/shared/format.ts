export const int = (v: number) => Math.round(v).toLocaleString("en-GB");
export const one = (v: number) => v.toLocaleString("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const pct = (v: number, d = 0) => `${(v * 100).toFixed(d)}%`;
export const eur = (v: number) => `€${Math.round(v).toLocaleString("en-GB")}`;

/** The two main designs first, then the ablations grouped by the area they take away. */
export const ORDER = [
  "as_found",
  "ai_on_green",
  "platform_all_tests",
  "platform_fixed_shards",
  "platform_nightly_only",
  "platform_no_quarantine",
  "platform_threshold_paging",
  "platform_no_grouping",
  "platform_symptoms_page",
  "platform_rules_only",
  "platform_no_idempotency",
  "platform_single_region",
  "platform",
];

export const NAME: Record<string, string> = {
  as_found: "As found",
  ai_on_green: "AI changes on green CI",
  platform_all_tests: "Every test, every PR",
  platform_fixed_shards: "Fixed shards",
  platform_nightly_only: "Full run nightly only",
  platform_no_quarantine: "No flake quarantine",
  platform_threshold_paging: "Threshold paging",
  platform_no_grouping: "No alert grouping",
  platform_symptoms_page: "Symptoms page",
  platform_rules_only: "Guard without AI tier",
  platform_no_idempotency: "No idempotency keys",
  platform_single_region: "One region",
  platform: "Platform",
};

export const tone = (name: string) => (name === "platform" ? "text-platform" : name === "as_found" ? "text-asFound" : "text-copy");
