/**
 * The tRPC router the product calls to start and check a vesting run. Starting is idempotent too: the workflow id
 * is the company and run date, and a second start for the same run returns the run already in flight.
 */
import { WorkflowExecutionAlreadyStartedError, type Client } from "@temporalio/client";
import { initTRPC } from "@trpc/server";
import { z } from "zod";
import { observed } from "./metrics";

export const TASK_QUEUE = "equity";
const t = initTRPC.context<{ temporal: Client }>().create();

/** Every procedure is counted for the SLOs: requests by code, and requests slower than a second. */
const counted = t.procedure.use(({ path, next }) =>
  observed(path, async () => {
    const r = await next();
    if (!r.ok) throw r.error;
    return r;
  }),
);

const RunInput = z.object({ companyId: z.string().min(1).max(64), runDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/) });

export const runId = (companyId: string, runDate: string) => `vest-${companyId}-${runDate}`;

export const router = t.router({
  startVestingRun: counted.input(RunInput).mutation(async ({ ctx, input }) => {
    const id = runId(input.companyId, input.runDate);
    try {
      await ctx.temporal.workflow.start("vestingRun", { taskQueue: TASK_QUEUE, workflowId: id, args: [input] });
      return { runId: id, started: true };
    } catch (e) {
      if (e instanceof WorkflowExecutionAlreadyStartedError) return { runId: id, started: false };
      throw e;
    }
  }),
  runStatus: counted.input(RunInput).query(async ({ ctx, input }) => {
    const d = await ctx.temporal.workflow.getHandle(runId(input.companyId, input.runDate)).describe();
    return { status: d.status.name };
  }),
});

export type Router = typeof router;
export const createCaller = t.createCallerFactory(router);
