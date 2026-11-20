/**
 * The monthly vesting run for one company, as a Temporal workflow: it survives worker crashes and region
 * failover by replaying its history, and retries each batch until it lands. Deterministic: no clocks, no I/O.
 */
import { proxyActivities, workflowInfo } from "@temporalio/workflow";
import type { Activities } from "./activities";

const { grantBatches, vestBatch, completeRun } = proxyActivities<Activities>({
  startToCloseTimeout: "2 minutes",
  retry: { initialInterval: "1 second", backoffCoefficient: 2, maximumAttempts: 10 },
});

export type RunInput = { companyId: string; runDate: string };
export type RunResult = { batches: number; due: number; written: number };

export async function vestingRun({ companyId, runDate }: RunInput): Promise<RunResult> {
  const batches = await grantBatches(companyId);
  let due = 0;
  let written = 0;
  for (let b = 0; b < batches; b++) {
    const r = await vestBatch(companyId, runDate, b);
    due += r.due;
    written += r.written;
  }
  await completeRun(workflowInfo().workflowId, written);
  return { batches, due, written };
}
