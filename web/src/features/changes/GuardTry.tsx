/** Run the plan guard on an example plan, or on a plan pasted from `terraform show -json`. */
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { type ApiError, post, useResource } from "../../shared/api";
import type { Example, Verdict } from "../../shared/types";
import { EmptyState, ErrorState, Skeleton } from "../../shared/ui/states";
import { motionTokens } from "../../theme/motion";

const DECISION = {
  apply: { word: "Applies after CI", cls: "border-good bg-goodWash text-good" },
  review: { word: "A person reviews it", cls: "border-warn bg-warnWash text-warn" },
  block: { word: "Blocked", cls: "border-bad bg-badWash text-bad" },
} as const;

const LEVEL = { block: "text-bad", review: "text-warn", info: "text-muted" } as const;

const TITLE: Record<string, string> = {
  routine: "Routine: a private bucket",
  public_lb_443: "Load balancer open on 443",
  db_open: "Database port open to the internet",
  replace_database: "Database cluster replaced",
};

export function GuardTry() {
  const ex = useResource<Example[]>("/api/guard/examples");
  const [picked, setPicked] = useState<string | null>(null);
  const [plan, setPlan] = useState("");
  const [commits, setCommits] = useState("");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const pick = (e: Example) => {
    setPicked(e.name);
    setPlan(JSON.stringify(e.plan, null, 1));
    setCommits(e.commits);
    setVerdict(null);
    setFailure(null);
  };
  useEffect(() => {
    if (ex.data && ex.data.length && picked === null) pick(ex.data.find((e) => e.name === "db_open") ?? ex.data[0]!);
  }, [ex.data, picked]);

  if (ex.loading) return <Skeleton label="Loading example plans" rows={4} />;
  if (ex.error) return <ErrorState error={ex.error} retry={ex.retry} what="the example plans" />;
  if (!ex.data?.length) return <EmptyState title="No example plans">Add a plan to infra/guard-examples, or paste one below.</EmptyState>;

  const run = async () => {
    setRunning(true);
    setFailure(null);
    try {
      let parsed: unknown;
      try {
        parsed = JSON.parse(plan);
      } catch {
        throw new Error("The plan is not valid JSON. Paste the output of terraform show -json plan.out.");
      }
      setVerdict(await post<Verdict>("/api/guard", { plan: parsed, commits }));
    } catch (e) {
      setVerdict(null);
      setFailure((e as ApiError | Error).message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section aria-labelledby="try" className="flex flex-col gap-4 rounded-card bg-sheet p-5">
      <h2 id="try" className="text-title font-bold">Try the guard</h2>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Example plans">
        {ex.data.map((e) => (
          <button
            key={e.name}
            type="button"
            aria-pressed={picked === e.name}
            onClick={() => pick(e)}
            className={`rounded-pill border px-4 py-2 text-small font-semibold transition-colors ${
              picked === e.name ? "border-focus bg-focus text-sheet" : "border-line text-copy hover:border-ink"
            }`}
          >
            {TITLE[e.name] ?? e.name}
          </button>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <label className="flex flex-col gap-1 text-small font-semibold text-ink">
          Plan (terraform show -json)
          <textarea value={plan} onChange={(e) => setPlan(e.target.value)} spellCheck={false} rows={14} className="rounded-soft border border-line bg-ground p-3 font-code text-small font-normal text-copy" />
        </label>
        <label className="flex flex-col gap-1 text-small font-semibold text-ink">
          Commit messages
          <textarea value={commits} onChange={(e) => setCommits(e.target.value)} spellCheck={false} rows={14} className="rounded-soft border border-line bg-ground p-3 font-code text-small font-normal text-copy" />
        </label>
      </div>
      <div>
        <button type="button" onClick={run} disabled={running} className="rounded-pill bg-ink px-5 py-2 font-semibold text-sheet disabled:opacity-60">
          {running ? "Running the guard…" : "Run the guard"}
        </button>
      </div>
      {failure && (
        <p role="alert" className="rounded-soft border border-bad bg-badWash p-3 text-bad">
          {failure}
        </p>
      )}
      <AnimatePresence mode="wait">
        {verdict && (
          <motion.div
            key={`${picked}-${verdict.decision}-${verdict.risk}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: motionTokens.quick * 2, ease: motionTokens.ease }}
            className={`flex flex-col gap-3 rounded-card border-l-rule p-4 ${DECISION[verdict.decision].cls}`}
            aria-live="polite"
          >
            <p className="text-lead font-bold">{DECISION[verdict.decision].word}</p>
            <p className="text-small text-copy">
              {verdict.resources} resources, risk {verdict.risk}
              {verdict.ai ? ", written with an AI assistant (Co-Authored-By trailer)" : ", written by a person"}
            </p>
            {verdict.findings.length === 0 ? (
              <p className="text-small text-copy">No findings.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {verdict.findings.map((f, i) => (
                  <li key={i} className="grid gap-1 text-small sm:grid-cols-[5rem_14rem_1fr]">
                    <span className={`font-semibold ${LEVEL[f.level]}`}>{f.level}</span>
                    <code className="font-code text-ink">{f.rule}</code>
                    <span className="text-copy">
                      <code className="font-code">{f.address}</code>: {f.detail}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
