export type Parts = {
  waiting_for_ci: number;
  flaky_reds: number;
  broken_main: number;
  pages: number;
  change_review: number;
  job_repairs: number;
};

export type DesignSummary = {
  label: string;
  feedback_p50: number;
  feedback_p90: number;
  flaky_red_per_week: number;
  flaky_red_ci: [number, number];
  escaped_share: number;
  main_broken_hours_per_week: number;
  runner_eur_per_month: number;
  pages_per_week: number;
  pages_ci: [number, number];
  false_pages_per_week: number;
  after_hours_pages_per_week: number;
  detected_share: number;
  minutes_to_page: number | null;
  harmful: number;
  harmful_applied: number;
  review_hours_per_week: number;
  hours_to_apply_median: number;
  false_blocks_per_week: number;
  duplicate_grants: number;
  late_runs: number;
  job_runs: number;
  manual_hours_per_month: number;
  standby_eur_per_month: number;
  down_minutes_per_month: number;
  engineer_hours_per_week: number;
  engineer_hours_vs_as_found_ci: [number, number];
  hours_parts: Parts;
};

export type Report = {
  designs: Record<string, DesignSummary>;
  world: { orgs: number; seeds: number[]; weeks: number; prs: number; incidents: number; page_worthy: number; changes: number; job_runs: number };
};

export type Results = { dev: Report; heldout: Report | null; gate: { dev: string[]; heldout: string[] | null } };

export type Finding = { level: "block" | "review" | "info"; address: string; rule: string; detail: string };
export type Verdict = { decision: "block" | "review" | "apply"; risk: number; ai: boolean; findings: Finding[]; resources: number };
export type Example = { name: string; plan: { resource_changes: unknown[] }; commits: string };
