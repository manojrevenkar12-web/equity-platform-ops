/** Delivery, on-call and jobs: a sentence with the result, then the designs that test it. */
import { eur, int, one, pct } from "../../shared/format";
import type { DesignSummary, Report } from "../../shared/types";
import { ErrorState, Skeleton } from "../../shared/ui/states";
import { useResults } from "../../shared/useResults";
import { AreaTable, type Column } from "./AreaTable";

type Area = {
  designs: string[];
  headline: (a: DesignSummary, p: DesignSummary) => string;
  lead: (r: Report) => string;
  title: string;
  columns: Column[];
};

export const AREAS: Record<"delivery" | "oncall" | "jobs", Area> = {
  delivery: {
    designs: ["as_found", "platform_all_tests", "platform_fixed_shards", "platform_nightly_only", "platform_no_quarantine", "platform"],
    headline: (a, p) => `Pull requests hear back in ${one(p.feedback_p90)} minutes, not ${one(a.feedback_p90)}`,
    lead: (r) =>
      `90th percentile feedback over ${int(r.world.prs)} pull requests. Only the tests a change can reach run on the PR, sharded by duration; a sequential test quarantines flaky tests after a few runs; main runs everything hourly to catch what selection misses.`,
    title: "Delivery",
    columns: [
      { label: "Feedback p50 (min)", value: (d) => one(d.feedback_p50) },
      { label: "Feedback p90 (min)", value: (d) => one(d.feedback_p90) },
      { label: "Flaky reds a week", value: (d) => `${one(d.flaky_red_per_week)} (${one(d.flaky_red_ci[0])}–${one(d.flaky_red_ci[1])})` },
      { label: "Main broken (h/week)", value: (d) => one(d.main_broken_hours_per_week) },
      { label: "Defects found on main", value: (d) => pct(d.escaped_share), note: "Share of real defects that passed the PR and were caught by the run on main" },
      { label: "Runners a month", value: (d) => eur(d.runner_eur_per_month) },
    ],
  },
  oncall: {
    designs: ["as_found", "platform_threshold_paging", "platform_no_grouping", "platform_symptoms_page", "platform"],
    headline: (a, p) => `${one(p.pages_per_week)} pages a week instead of ${one(a.pages_per_week)}, still paging for ${pct(p.detected_share)} of what matters`,
    lead: (r) =>
      `${int(r.world.page_worthy)} incidents burned enough error budget to deserve a page. Pages come from budget-burn alerts on two windows, grouped by service; CPU, restarts and replication lag become tickets.`,
    title: "On-call",
    columns: [
      { label: "Pages a week", value: (d) => `${one(d.pages_per_week)} (${one(d.pages_ci[0])}–${one(d.pages_ci[1])})` },
      { label: "False pages a week", value: (d) => one(d.false_pages_per_week) },
      { label: "After hours a week", value: (d) => one(d.after_hours_pages_per_week) },
      { label: "Page-worthy paged", value: (d) => pct(d.detected_share) },
      { label: "Minutes to page", value: (d) => (d.minutes_to_page == null ? "–" : one(d.minutes_to_page)) },
    ],
  },
  jobs: {
    designs: ["as_found", "platform_no_idempotency", "platform_single_region", "platform"],
    headline: (a, p) => `${int(p.duplicate_grants)} duplicate vesting records instead of ${int(a.duplicate_grants)}`,
    lead: (r) =>
      `${int(r.world.job_runs)} monthly vesting runs. Cron jobs that die halfway are rerun by hand and write twice; Temporal workflows retry each batch, and an idempotency key on every tranche turns the second write into nothing. Workers poll in two regions.`,
    title: "Vesting runs",
    columns: [
      { label: "Duplicate records", value: (d) => int(d.duplicate_grants) },
      { label: "Late runs", value: (d) => int(d.late_runs) },
      { label: "API down (min/month)", value: (d) => one(d.down_minutes_per_month) },
      { label: "Manual repair (h/month)", value: (d) => one(d.manual_hours_per_month) },
      { label: "Second region a month", value: (d) => eur(d.standby_eur_per_month) },
    ],
  },
};

export function AreaView({ area }: { area: keyof typeof AREAS }) {
  const { data, error, loading, retry } = useResults();
  const cfg = AREAS[area];
  if (loading) return <Skeleton label={`Loading ${cfg.title.toLowerCase()}`} />;
  if (error || !data) return <ErrorState error={error!} retry={retry} what={cfg.title.toLowerCase()} />;
  const r = data.heldout ?? data.dev;
  const rows = cfg.designs.filter((n) => r.designs[n]).map((n) => [n, r.designs[n]!] as [string, DesignSummary]);
  return (
    <div className="flex flex-col gap-6">
      <section className="flex max-w-hero flex-col gap-3">
        <h1 className="text-title font-bold">{cfg.headline(r.designs.as_found!, r.designs.platform!)}</h1>
        <p className="max-w-prose">{cfg.lead(r)}</p>
      </section>
      <AreaTable title={cfg.title} rows={rows} columns={cfg.columns} />
    </div>
  );
}
