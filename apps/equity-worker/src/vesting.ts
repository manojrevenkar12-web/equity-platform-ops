/**
 * Vesting schedules: which tranches of a grant vest on a run date. Pure, so the same input always gives the same
 * tranches, and a retried run computes exactly what the first attempt did.
 */
export type Grant = {
  grantId: string;
  holderId: string;
  shares: number;
  start: string; // ISO date the vesting clock starts
  months: number; // total vesting months
  cliffMonths: number; // nothing vests before the cliff; the cliff tranche catches up
};

export type Tranche = { grantId: string; holderId: string; tranche: number; shares: number; vestsOn: string };

function monthsBetween(a: Date, b: Date): number {
  return (b.getUTCFullYear() - a.getUTCFullYear()) * 12 + (b.getUTCMonth() - a.getUTCMonth()) - (b.getUTCDate() < a.getUTCDate() ? 1 : 0);
}

function addMonths(d: Date, m: number): string {
  const x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + m, d.getUTCDate()));
  return x.toISOString().slice(0, 10);
}

/** Whole shares per month; the remainder vests with the last tranche so the total always matches the grant. */
export function tranchesDue(g: Grant, runDate: string): Tranche[] {
  const start = new Date(`${g.start}T00:00:00Z`);
  const run = new Date(`${runDate}T00:00:00Z`);
  const elapsed = Math.min(monthsBetween(start, run), g.months);
  if (elapsed < g.cliffMonths) return [];
  const per = Math.floor(g.shares / g.months);
  const out: Tranche[] = [];
  for (let m = 1; m <= elapsed; m++) {
    const shares = m === g.months ? g.shares - per * (g.months - 1) : per;
    out.push({ grantId: g.grantId, holderId: g.holderId, tranche: m, shares, vestsOn: addMonths(start, m) });
  }
  return out;
}

export const trancheKey = (t: Pick<Tranche, "grantId" | "tranche">) => `${t.grantId}#${t.tranche}`;
