/**
 * Against a real Temporal dev server and a real MongoDB wire protocol (MongoDB in CI, FerretDB locally):
 * a worker that dies after its write landed is retried, and no tranche is vested twice.
 */
import path from "node:path";
import { TestWorkflowEnvironment } from "@temporalio/testing";
import { Worker } from "@temporalio/worker";
import { type Db, MongoClient } from "mongodb";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createActivities, ensureIndexes } from "../src/activities";
import { boundActivities } from "../src/activities.entry";
import { TASK_QUEUE, createCaller, runId } from "../src/api";
import { registry } from "../src/metrics";
import { tranchesDue } from "../src/vesting";

let env: TestWorkflowEnvironment;
let mongo: MongoClient;
let db: Db;

function grants(companyId: string, n: number) {
  return Array.from({ length: n }, (_, i) => ({
    companyId, grantId: `${companyId}-g${String(i).padStart(4, "0")}`, holderId: `h${i}`, shares: 1200 + i,
    start: "2024-03-01", months: 48, cliffMonths: 12,
  }));
}

beforeAll(async () => {
  const cli = process.env.TEMPORAL_CLI;
  env = await TestWorkflowEnvironment.createLocal(cli ? { server: { executable: { type: "existing-path", path: cli } } } : {});
  mongo = await new MongoClient(process.env.MONGO_URL ?? "mongodb://127.0.0.1:27017").connect();
  db = mongo.db(`equity_test_${Date.now()}`);
  await ensureIndexes(db);
});

afterAll(async () => {
  await db?.dropDatabase().catch(() => undefined);
  await mongo?.close();
  await env?.teardown();
});

async function runWith(faults: { crashAfterWriteOnAttempt?: number }, companyId: string) {
  await db.collection("grants").insertMany(grants(companyId, 120));
  const worker = await Worker.create({
    connection: env.nativeConnection, taskQueue: TASK_QUEUE,
    workflowsPath: path.resolve(__dirname, "../src/workflows.ts"), activities: boundActivities(db, faults),
  });
  const caller = createCaller({ temporal: env.client });
  return worker.runUntil(async () => {
    const first = await caller.startVestingRun({ companyId, runDate: "2026-11-01" });
    const second = await caller.startVestingRun({ companyId, runDate: "2026-11-01" });
    const result = await env.client.workflow.getHandle(runId(companyId, "2026-11-01")).result();
    return { first, second, result };
  });
}

describe("vesting run on Temporal", () => {
  it("survives a worker lost after its write, without vesting anything twice", async () => {
    const { first, second, result } = await runWith({ crashAfterWriteOnAttempt: 1 }, "acme");
    expect(first.started).toBe(true);
    expect(second.started).toBe(false); // the same run is not started twice
    const expected = grants("acme", 120).flatMap((g) => tranchesDue(g, "2026-11-01")).length;
    const stored = await db.collection("vesting_events").countDocuments({ companyId: "acme" });
    expect(stored).toBe(expected);
    expect(result.batches).toBe(3);
    const metrics = await registry.metrics();
    expect(metrics).toMatch(/trpc_requests_total\{path="startVestingRun",code="OK"\} 2/);
  });

  it("writes nothing new when a batch is run again by hand", async () => {
    const a = createActivities(db);
    const before = await db.collection("vesting_events").countDocuments({ companyId: "acme" });
    const again = await a.vestBatch("acme", "2026-11-01", 1);
    expect(again.written).toBe(0);
    expect(await db.collection("vesting_events").countDocuments({ companyId: "acme" })).toBe(before);
  });
});
