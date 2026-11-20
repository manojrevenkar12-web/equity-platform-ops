/** Wires activities with the attempt number Temporal passes, so retries are visible to the fault hook in tests. */
import { Context } from "@temporalio/activity";
import type { Db } from "mongodb";
import { type Faults, createActivities } from "./activities";

export function boundActivities(db: Db, faults: Faults = {}) {
  const a = createActivities(db, faults);
  return {
    grantBatches: a.grantBatches,
    completeRun: a.completeRun,
    vestBatch: (companyId: string, runDate: string, batch: number) =>
      a.vestBatch(companyId, runDate, batch, Context.current().info.attempt),
  };
}
