/**
 * Activities touch MongoDB. Every write carries an idempotency key (grant and tranche), backed by a unique index:
 * an activity that Temporal retries after a worker died mid-write meets its own earlier rows as duplicate-key
 * errors, which count as already written. A tranche cannot be vested twice.
 */
import { type Db, MongoBulkWriteError } from "mongodb";
import { type Grant, type Tranche, trancheKey, tranchesDue } from "./vesting";

export const BATCH = 50;

export async function ensureIndexes(db: Db): Promise<void> {
  await db.collection("vesting_events").createIndex({ key: 1 }, { unique: true, name: "idempotency_key" });
  await db.collection("vesting_runs").createIndex({ runId: 1 }, { unique: true });
}

/** Inserts the rows not yet present. Duplicate keys (11000) mean "already written"; any other error is raised. */
export async function insertOnce(db: Db, rows: Array<Record<string, unknown> & { key: string }>): Promise<number> {
  if (rows.length === 0) return 0;
  try {
    return (await db.collection("vesting_events").insertMany(rows, { ordered: false })).insertedCount;
  } catch (e) {
    if (e instanceof MongoBulkWriteError) {
      const errors = Array.isArray(e.writeErrors) ? e.writeErrors : [e.writeErrors];
      if (errors.every((w) => w.code === 11000)) return e.insertedCount;
    }
    throw e;
  }
}

export type Faults = { crashAfterWriteOnAttempt?: number };

export function createActivities(db: Db, faults: Faults = {}) {
  return {
    async grantBatches(companyId: string): Promise<number> {
      const n = await db.collection<Grant & { companyId: string }>("grants").countDocuments({ companyId });
      return Math.ceil(n / BATCH);
    },

    async vestBatch(companyId: string, runDate: string, batch: number, attempt = 1): Promise<{ due: number; written: number }> {
      const grants = await db
        .collection<Grant & { companyId: string }>("grants")
        .find({ companyId }, { projection: { _id: 0, companyId: 0 } })
        .sort({ grantId: 1 })
        .skip(batch * BATCH)
        .limit(BATCH)
        .toArray();
      const due: Tranche[] = grants.flatMap((g) => tranchesDue(g as Grant, runDate));
      const written = await insertOnce(db, due.map((t) => ({ ...t, key: trancheKey(t), companyId, runDate })));
      if (faults.crashAfterWriteOnAttempt === attempt && batch === 0) {
        throw new Error("worker lost after the write landed"); // the case a plain insert would duplicate
      }
      return { due: due.length, written };
    },

    async completeRun(runId: string, written: number): Promise<void> {
      await db.collection("vesting_runs").updateOne({ runId }, { $setOnInsert: { runId, written, at: new Date() } }, { upsert: true });
    },
  };
}

export type Activities = ReturnType<typeof createActivities>;
