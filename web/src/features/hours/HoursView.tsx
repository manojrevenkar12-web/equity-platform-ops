import { NAME, ORDER, int, one } from "../../shared/format";
import { ErrorState, Gate, Skeleton } from "../../shared/ui/states";
import { useResults } from "../../shared/useResults";
import { HoursBars, PARTS } from "./HoursBars";

export function HoursView() {
  const { data, error, loading, retry } = useResults();
  if (loading) return <Skeleton label="Loading the evaluation" rows={10} />;
  if (error || !data) return <ErrorState error={error!} retry={retry} what="the evaluation" />;
  const r = data.heldout ?? data.dev;
  const d = r.designs;
  const rows = ORDER.filter((n) => d[n]).map((n) => [n, d[n]!] as [string, (typeof d)[string]]);
  const a = d.as_found!;
  const p = d.platform!;
  const [lo, hi] = p.engineer_hours_vs_as_found_ci;
  const w = r.world;
  return (
    <div className="flex flex-col gap-7">
      <section className="flex max-w-hero flex-col gap-4">
        <h1 className="text-hero font-bold">
          {int(a.engineer_hours_per_week)} engineering hours lost a week as found, {int(p.engineer_hours_per_week)} on the platform
        </h1>
        <p className="max-w-prose text-lead">
          The same {w.orgs} simulated engineering orgs over {w.weeks} weeks each: {int(w.prs)} pull requests, {int(w.incidents)} incidents,{" "}
          {int(w.changes)} infrastructure changes and {int(w.job_runs)} vesting runs, with the same luck for every design. The platform saves{" "}
          {one(-hi)} to {one(-lo)} hours a week (95% interval, paired by org and week).
        </p>
        <div className="flex flex-wrap gap-4">
          <Gate fails={data.gate.dev} what="Development orgs" />
          <Gate fails={data.gate.heldout} what="Held-out orgs" />
        </div>
        <p className="text-small text-muted">{data.heldout ? "Showing the held-out orgs, run once." : "Showing the development orgs; the held-out run has not happened yet."}</p>
      </section>

      <section aria-labelledby="where" className="flex flex-col gap-4 rounded-card bg-sheet p-5">
        <h2 id="where" className="text-title font-bold">Where the hours go</h2>
        <HoursBars rows={rows} />
      </section>

      <section aria-labelledby="table" className="overflow-x-auto rounded-card bg-sheet p-5">
        <table className="min-w-table text-small" aria-labelledby="table">
          <caption id="table" className="pb-3 text-left text-lead font-bold text-ink">
            Hours a week, by design
          </caption>
          <thead>
            <tr className="border-b border-line text-left text-muted">
              <th scope="col" className="py-2 pr-4 font-semibold">Design</th>
              {PARTS.map((x) => (
                <th key={x.key} scope="col" className="py-2 pr-4 text-right font-semibold">{x.label}</th>
              ))}
              <th scope="col" className="py-2 text-right font-semibold">Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([n, x]) => (
              <tr key={n} className="border-b border-line last:border-0">
                <th scope="row" className="py-2 pr-4 text-left font-semibold text-ink">{NAME[n] ?? x.label}</th>
                {PARTS.map((k) => (
                  <td key={k.key} className="py-2 pr-4 text-right">{one(x.hours_parts[k.key])}</td>
                ))}
                <td className="py-2 text-right font-semibold text-ink">{one(x.engineer_hours_per_week)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
