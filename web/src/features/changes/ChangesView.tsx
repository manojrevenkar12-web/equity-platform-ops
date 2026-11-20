import { int, one } from "../../shared/format";
import type { DesignSummary } from "../../shared/types";
import { ErrorState, Skeleton } from "../../shared/ui/states";
import { useResults } from "../../shared/useResults";
import { AreaTable } from "../areas/AreaTable";
import { GuardTry } from "./GuardTry";

const DESIGNS = ["as_found", "ai_on_green", "platform_rules_only", "platform"];

export function ChangesView() {
  const { data, error, loading, retry } = useResults();
  if (loading) return <Skeleton label="Loading infrastructure changes" />;
  if (error || !data) return <ErrorState error={error!} retry={retry} what="infrastructure changes" />;
  const r = data.heldout ?? data.dev;
  const d = r.designs;
  const rows = DESIGNS.filter((n) => d[n]).map((n) => [n, d[n]!] as [string, DesignSummary]);
  const p = d.platform!;
  const a = d.as_found!;
  const ai = d.ai_on_green!;
  const ro = d.platform_rules_only!;
  return (
    <div className="flex flex-col gap-6">
      <section className="flex max-w-hero flex-col gap-3">
        <h1 className="text-title font-bold">
          {p.harmful_applied} of {p.harmful} harmful infrastructure changes applied, against {a.harmful_applied} with every change reviewed by a person
        </h1>
        <p className="max-w-prose">
          {int(r.world.changes)} Terraform changes, a third written with an AI assistant. Letting AI-written changes apply on green CI applied {ai.harmful_applied}.
          The guard reads each plan: it blocks what is never right, sends what needs judgement to a person, and applies the rest. Its AI tier (every
          AI-written IAM change reviewed) costs {one(p.review_hours_per_week - ro.review_hours_per_week)} review hours a week and stopped{" "}
          {ro.harmful_applied - p.harmful_applied} more harmful change{ro.harmful_applied - p.harmful_applied === 1 ? "" : "s"}: a close trade, kept for changes that touch access.
        </p>
      </section>
      <AreaTable
        title="Infrastructure changes"
        rows={rows}
        columns={[
          { label: "Harmful applied", value: (x) => `${x.harmful_applied} of ${x.harmful}` },
          { label: "Review (h/week)", value: (x) => one(x.review_hours_per_week) },
          { label: "Median hours to apply", value: (x) => one(x.hours_to_apply_median) },
          { label: "False blocks a week", value: (x) => one(x.false_blocks_per_week) },
        ]}
      />
      <GuardTry />
    </div>
  );
}
